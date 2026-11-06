from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update

from app.common.db import get_db
from app.common.identity import admin_user, current_user, revoke_sessions
from app.common.models import Product
from app.modules.commerce.models import (
    Category,
    Coupon,
    Notification,
    Order,
    Review,
    StoreSettings,
    SupportTicket,
    User,
)
from app.modules.commerce.schemas import (
    AdminOrderIn,
    CategoryIn,
    CouponIn,
    CouponOut,
    MessageOut,
    NotificationOut,
    OrderOut,
    ProductModerationIn,
    ShopProduct,
    StoreConfig,
    StoreSettingsIn,
    TicketIn,
    TicketOut,
    TicketReplyIn,
    UserOut,
    UserRoleIn,
)
from app.modules.commerce.service import (
    order_event,
    order_view,
    product_view,
    release_stock,
    store_config,
)

router = APIRouter(tags=["Administration and customer support"])


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(user=Depends(current_user), db=Depends(get_db)):
    return db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    ).all()


@router.post("/notifications/read", response_model=MessageOut)
def read_notifications(user=Depends(current_user), db=Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    db.commit()
    return MessageOut(message="Notifications marked as read")


@router.post("/support/tickets", response_model=TicketOut, status_code=201)
def contact(body: TicketIn, user=Depends(current_user), db=Depends(get_db)):
    open_count = db.scalar(
        select(func.count())
        .select_from(SupportTicket)
        .where(SupportTicket.user_id == user.id, SupportTicket.status == "open")
    )
    if open_count >= 10:
        raise HTTPException(429, "You already have ten open support requests")
    ticket = SupportTicket(user_id=user.id, **body.model_dump())
    db.add(ticket)
    db.commit()
    return ticket


@router.get("/support/tickets", response_model=list[TicketOut])
def tickets(user=Depends(current_user), db=Depends(get_db)):
    stmt = select(SupportTicket)
    if user.role != "admin":
        stmt = stmt.where(SupportTicket.user_id == user.id)
    return db.scalars(stmt.order_by(SupportTicket.created_at.desc()).limit(100)).all()


@router.post("/admin/tickets/{ticket_id}/reply", response_model=TicketOut)
def reply(ticket_id: UUID, body: TicketReplyIn, user=Depends(admin_user), db=Depends(get_db)):
    ticket = db.get(SupportTicket, str(ticket_id))
    if ticket is None:
        raise HTTPException(404, "Support request not found")
    ticket.response, ticket.status = body.response, body.status
    db.add(
        Notification(user_id=ticket.user_id, title="Support replied", message=body.response[:1000])
    )
    db.commit()
    return ticket


@router.get("/admin/overview")
def overview(user=Depends(admin_user), db=Depends(get_db)):
    orders = db.scalar(select(func.count()).select_from(Order)) or 0
    revenue = (
        db.scalar(
            select(func.sum(Order.total_minor)).where(
                Order.payment_status == "paid", Order.status.notin_(["cancelled", "returned"])
            )
        )
        or 0
    )
    statuses = dict(db.execute(select(Order.status, func.count()).group_by(Order.status)).all())
    return {
        "orders": orders,
        "paid_revenue_minor": revenue,
        "users": db.scalar(select(func.count()).select_from(User).where(User.role != "guest")) or 0,
        "products": db.scalar(
            select(func.count()).select_from(Product).where(Product.is_archived.is_(False))
        )
        or 0,
        "low_stock": db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.stock < 5, Product.is_archived.is_(False))
        )
        or 0,
        "open_tickets": db.scalar(
            select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "open")
        )
        or 0,
        "order_statuses": statuses,
        "currency": store_config(db).currency,
    }


@router.get("/admin/users", response_model=list[UserOut])
def users(user=Depends(admin_user), db=Depends(get_db)):
    return db.scalars(
        select(User).where(User.role != "guest").order_by(User.created_at.desc()).limit(200)
    ).all()


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def update_user(user_id: UUID, body: UserRoleIn, user=Depends(admin_user), db=Depends(get_db)):
    account = db.get(User, str(user_id))
    if account is None:
        raise HTTPException(404, "Account not found")
    if account.id == user.id and (body.role != "admin" or not body.is_active):
        raise HTTPException(409, "You cannot remove your own administrator access")
    changed = account.role != body.role or account.is_active != body.is_active
    account.role, account.is_active = body.role, body.is_active
    if changed:
        revoke_sessions(db, account.id)
    db.commit()
    return account


@router.get("/admin/products", response_model=list[ShopProduct])
def all_products(user=Depends(admin_user), db=Depends(get_db)):
    return [
        product_view(db, p, True)
        for p in db.scalars(
            select(Product)
            .where(Product.is_archived.is_(False))
            .order_by(Product.created_at.desc())
            .limit(200)
        )
    ]


@router.patch("/admin/products/{product_id}", response_model=ShopProduct)
def moderate(
    product_id: UUID, body: ProductModerationIn, user=Depends(admin_user), db=Depends(get_db)
):
    product = db.get(Product, str(product_id))
    if product is None or product.is_archived:
        raise HTTPException(404, "Product not found")
    if body.is_listed and (not product.images or product.price_minor < 1):
        raise HTTPException(422, "A listing requires photos and a price")
    product.is_listed, product.featured = body.is_listed, body.featured
    db.commit()
    return product_view(db, product, True)


@router.get("/admin/orders", response_model=list[OrderOut])
def all_orders(user=Depends(admin_user), db=Depends(get_db)):
    return [
        order_view(db, o)
        for o in db.scalars(select(Order).order_by(Order.created_at.desc()).limit(200))
    ]


@router.post("/admin/orders/{order_id}", response_model=OrderOut)
def manage_order(order_id: UUID, body: AdminOrderIn, user=Depends(admin_user), db=Depends(get_db)):
    order = db.scalar(select(Order).where(Order.id == str(order_id)).with_for_update())
    if order is None:
        raise HTTPException(404, "Order not found")
    if body.action == "mark_cod_paid":
        if order.payment_method != "cod" or order.status != "delivered":
            raise HTTPException(409, "Only delivered COD orders can be marked paid")
        order.payment_status = "paid"
    elif body.action == "reject_return":
        if order.status != "return_requested":
            raise HTTPException(409, "There is no pending return request")
        order.status = "delivered"
    elif body.action == "refund":
        if order.payment_status != "paid":
            raise HTTPException(409, "This order has no recorded payment to refund")
        if order.status not in {"returned", "cancelled"}:
            raise HTTPException(409, "Cancel or accept the return before refunding")
        if order.payment_method == "stripe":
            from app.modules.commerce.payments import refund_hosted

            refund = refund_hosted(order)
            if refund.status != "succeeded":
                raise HTTPException(409, "Provider refund is pending; check the provider dashboard")
        order.payment_status = "refunded"
    else:
        expected = {"placed", "processing"} if body.action == "cancel" else {"return_requested"}
        if order.status not in expected:
            raise HTTPException(409, "This order cannot make that transition")
        if (
            order.payment_method == "stripe"
            and order.stripe_session_id
            and order.payment_status != "paid"
        ):
            raise HTTPException(409, "Expire the hosted session before cancelling this order")
        release_stock(db, order)
        order.status = "cancelled" if body.action == "cancel" else "returned"
        if order.payment_method == "demo":
            order.payment_status = "refunded"
    order_event(db, order, f"Support updated the order: {body.action.replace('_', ' ')}.")
    db.commit()
    return order_view(db, order)


@router.get("/admin/coupons", response_model=list[CouponOut])
def coupons(user=Depends(admin_user), db=Depends(get_db)):
    return db.scalars(select(Coupon).order_by(Coupon.code)).all()


@router.put("/admin/coupons/{code}", response_model=CouponOut)
def save_coupon(code: str, body: CouponIn, user=Depends(admin_user), db=Depends(get_db)):
    if code.upper() != body.code:
        raise HTTPException(422, "Coupon code does not match")
    coupon = db.get(Coupon, body.code)
    if coupon is None:
        coupon = Coupon(code=body.code)
        db.add(coupon)
    for key, value in body.model_dump().items():
        setattr(coupon, key, value)
    db.commit()
    return coupon


@router.get("/admin/categories", response_model=list[CategoryIn])
def categories(user=Depends(admin_user), db=Depends(get_db)):
    return [
        CategoryIn.model_validate(c, from_attributes=True) for c in db.scalars(select(Category))
    ]


@router.put("/admin/categories/{slug}", response_model=CategoryIn)
def category(slug: str, body: CategoryIn, user=Depends(admin_user), db=Depends(get_db)):
    if body.slug != slug:
        raise HTTPException(422, "Category slug does not match")
    item = db.get(Category, slug)
    if item is None:
        item = Category(slug=slug)
        db.add(item)
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    if not body.is_active:
        db.execute(update(Product).where(Product.category == slug).values(is_listed=False))
    db.commit()
    return body


@router.put("/admin/settings", response_model=StoreConfig)
def settings(body: StoreSettingsIn, user=Depends(admin_user), db=Depends(get_db)):
    record = db.get(StoreSettings, 1)
    if record is None:
        record = StoreSettings(id=1)
        db.add(record)
    for key, value in body.model_dump().items():
        setattr(record, key, value)
    db.commit()
    return store_config(db)


@router.get("/admin/reviews")
def all_reviews(user=Depends(admin_user), db=Depends(get_db)):
    return [
        {
            "id": r.id,
            "title": r.title,
            "body": r.body,
            "rating": r.rating,
            "is_visible": r.is_visible,
            "product_id": r.product_id,
        }
        for r in db.scalars(select(Review).order_by(Review.created_at.desc()).limit(200))
    ]


@router.post("/admin/reviews/{review_id}/visibility", response_model=MessageOut)
def visibility(review_id: UUID, visible: bool, user=Depends(admin_user), db=Depends(get_db)):
    review = db.get(Review, str(review_id))
    if review is None:
        raise HTTPException(404, "Review not found")
    review.is_visible = visible
    db.commit()
    return MessageOut(message="Review visibility updated")
