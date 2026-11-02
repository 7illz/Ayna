from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError

from app.common.db import get_db
from app.common.identity import cart_user, current_user, seller_user
from app.common.models import Product
from app.modules.commerce.models import CartItem, Coupon, Order, OrderItem, User, Variant
from app.modules.commerce.schemas import (
    CartIn,
    CartOut,
    CheckoutIn,
    FulfillIn,
    MessageOut,
    OrderOut,
    QuantityIn,
    QuoteIn,
    ReturnIn,
)
from app.modules.commerce.service import (
    aggregate_fulfillment,
    cart_quote,
    listed,
    order_event,
    order_view,
    release_stock,
    selection,
    store_config,
)

router = APIRouter(tags=["Cart, checkout and orders"])


def lock_customer(db, user_id):
    if db.get_bind().dialect.name == "sqlite":
        # SQLite development mode has no row locks; serialize cart writes before reading stock.
        db.execute(text("BEGIN IMMEDIATE"))
    db.scalar(select(User).where(User.id == user_id).with_for_update())


@router.get("/cart", response_model=CartOut)
def get_cart(user=Depends(cart_user), db=Depends(get_db)):
    return cart_quote(db, user.id)


@router.post("/cart/items", response_model=CartOut)
def add_to_cart(body: CartIn, user=Depends(cart_user), db=Depends(get_db)):
    lock_customer(db, user.id)
    product = listed(db, str(body.product_id), True)
    key = str(body.variant_id) if body.variant_id else "default"
    inventory, _, _, _ = selection(db, product, key, True)
    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id,
            CartItem.product_id == product.id,
            CartItem.variant_key == key,
        )
    )
    quantity = body.quantity + (item.quantity if item else 0)
    if quantity > 99 or quantity > inventory.stock:
        raise HTTPException(409, "There is not enough stock for that quantity")
    if item:
        item.quantity = quantity
    else:
        if len(db.scalars(select(CartItem.id).where(CartItem.user_id == user.id)).all()) >= 50:
            raise HTTPException(422, "Your cart has reached its item limit")
        db.add(CartItem(user_id=user.id, product_id=product.id, variant_key=key, quantity=quantity))
    db.commit()
    return cart_quote(db, user.id)


@router.patch("/cart/items/{item_id}", response_model=CartOut)
def update_cart(item_id: UUID, body: QuantityIn, user=Depends(cart_user), db=Depends(get_db)):
    lock_customer(db, user.id)
    item = db.get(CartItem, str(item_id))
    if item is None or item.user_id != user.id:
        raise HTTPException(404, "Cart item not found")
    product = listed(db, item.product_id, True)
    inventory, _, _, _ = selection(db, product, item.variant_key, True)
    if body.quantity > inventory.stock:
        raise HTTPException(409, "There is not enough stock for that quantity")
    item.quantity = body.quantity
    db.commit()
    return cart_quote(db, user.id)


@router.delete("/cart/items/{item_id}", response_model=CartOut)
def remove_cart(item_id: UUID, user=Depends(cart_user), db=Depends(get_db)):
    lock_customer(db, user.id)
    item = db.get(CartItem, str(item_id))
    if item is None or item.user_id != user.id:
        raise HTTPException(404, "Cart item not found")
    db.delete(item)
    db.commit()
    return cart_quote(db, user.id)


@router.post("/cart/quote", response_model=CartOut)
def quote(body: QuoteIn, user=Depends(cart_user), db=Depends(get_db)):
    return cart_quote(db, user.id, body.coupon_code)


@router.post("/checkout", response_model=OrderOut, status_code=201)
def checkout(
    body: CheckoutIn,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user=Depends(current_user),
    db=Depends(get_db),
):
    lock_customer(db, user.id)
    existing = db.scalar(
        select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key)
    )
    if existing:
        return order_view(db, existing)
    if body.payment_method not in store_config(db).payment_methods:
        raise HTTPException(422, "This payment method is not configured")
    cart = cart_quote(db, user.id, body.coupon_code, True)
    if not cart.items:
        raise HTTPException(422, "Your cart is empty")
    if any(not line.available or line.unit_price_minor < 1 for line in cart.items):
        raise HTTPException(409, "Some cart items are no longer available; update your cart")
    order = Order(
        id=str(uuid4()),
        number=f"AY-{datetime.now(UTC):%y%m%d}-{uuid4().hex[:8].upper()}",
        user_id=user.id,
        idempotency_key=idempotency_key,
        payment_method=body.payment_method,
        payment_status="paid" if body.payment_method == "demo" else "pending",
        currency=cart.currency,
        subtotal_minor=cart.subtotal_minor,
        discount_minor=cart.discount_minor,
        shipping_minor=cart.shipping_minor,
        tax_minor=cart.tax_minor,
        total_minor=cart.total_minor,
        coupon_code=cart.coupon_code,
        shipping_address=body.address.model_dump(),
        notes=body.notes,
    )
    db.add(order)
    db.flush()
    for line in cart.items:
        key = line.variant_id or "default"
        product = db.get(Product, line.product.id)
        inventory, price, label, sku = selection(db, product, key, True)
        inventory_class = Product if key == "default" else Variant
        claimed = db.scalar(
            update(inventory_class)
            .where(inventory_class.id == inventory.id, inventory_class.stock >= line.quantity)
            .values(stock=inventory_class.stock - line.quantity)
            .returning(inventory_class.id)
        )
        if claimed is None:
            db.rollback()
            raise HTTPException(409, "Stock changed during checkout; refresh your cart")
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                seller_id=product.seller_id,
                variant_key=key,
                name=product.name,
                variant_label=label,
                sku=sku,
                unit_price_minor=price,
                quantity=line.quantity,
            )
        )
    if cart.coupon_code:
        db.execute(
            update(Coupon)
            .where(Coupon.code == cart.coupon_code)
            .values(used_count=Coupon.used_count + 1)
        )
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    order_event(
        db,
        order,
        "Order placed. Demo payment recorded; no money charged."
        if body.payment_method == "demo"
        else "Order placed. Your items are reserved.",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This checkout was already submitted; check your orders") from exc
    return order_view(db, order)


def owned_order(db, order_id, user, lock=False):
    stmt = select(Order).where(Order.id == str(order_id))
    if user.role != "admin":
        stmt = stmt.where(Order.user_id == user.id)
    order = db.scalar(stmt.with_for_update() if lock else stmt)
    if order is None:
        raise HTTPException(404, "Order not found")
    return order


@router.get("/orders", response_model=list[OrderOut])
def my_orders(user=Depends(current_user), db=Depends(get_db)):
    orders = db.scalars(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(100)
    )
    return [order_view(db, o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderOut)
def order_detail(order_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    return order_view(db, owned_order(db, order_id, user))


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    order = owned_order(db, order_id, user, True)
    if order.status == "cancelled":
        return order_view(db, order)
    if order.status != "placed":
        raise HTTPException(409, "This order is already being fulfilled; contact support")
    if order.payment_method == "stripe" and (
        order.stripe_session_id or order.payment_status == "paid"
    ):
        raise HTTPException(409, "Contact support to cancel a hosted-payment order")
    release_stock(db, order)
    order.status = "cancelled"
    if order.payment_method == "demo":
        order.payment_status = "refunded"
    order_event(db, order, "Order cancelled and inventory restored.")
    db.commit()
    return order_view(db, order)


@router.post("/orders/{order_id}/return", response_model=OrderOut)
def request_return(order_id: UUID, body: ReturnIn, user=Depends(current_user), db=Depends(get_db)):
    order = owned_order(db, order_id, user, True)
    if order.status != "delivered":
        raise HTTPException(409, "Returns can be requested after delivery")
    order.status, order.return_reason = "return_requested", body.reason
    order_event(db, order, "Return requested. Support will review the request.")
    db.commit()
    return order_view(db, order)


@router.get("/seller/orders", response_model=list[OrderOut])
def seller_orders(user=Depends(seller_user), db=Depends(get_db)):
    orders = db.scalars(
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(OrderItem.seller_id == user.id)
        .distinct()
        .order_by(Order.created_at.desc())
        .limit(100)
    )
    return [order_view(db, order, user.id) for order in orders]


@router.post("/seller/order-items/{item_id}/fulfill", response_model=MessageOut)
def fulfill(item_id: UUID, body: FulfillIn, user=Depends(seller_user), db=Depends(get_db)):
    item = db.get(OrderItem, str(item_id))
    if item is None or (item.seller_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Order item not found")
    order = db.scalar(select(Order).where(Order.id == item.order_id).with_for_update())
    if order.status in {"cancelled", "return_requested", "returned"}:
        raise HTTPException(409, "This order cannot be fulfilled")
    if order.payment_method == "stripe" and order.payment_status != "paid":
        raise HTTPException(409, "Payment must be confirmed before fulfillment")
    allowed = {"pending": "processing", "processing": "shipped", "shipped": "delivered"}
    if allowed.get(item.fulfillment_status) != body.status:
        raise HTTPException(409, "Follow processing, shipped, then delivered")
    if body.status == "shipped" and not body.tracking_number.strip():
        raise HTTPException(422, "Add a tracking number before shipping")
    item.fulfillment_status = body.status
    if body.tracking_number:
        item.tracking_number, item.courier = body.tracking_number, body.courier
    db.flush()
    aggregate_fulfillment(db, order)
    order_event(db, order, f"{item.name}: {body.status}.")
    db.commit()
    return MessageOut(message="Fulfillment updated")
