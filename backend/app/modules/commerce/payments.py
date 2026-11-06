import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.common.config import get_settings
from app.common.db import get_db
from app.common.identity import current_user
from app.modules.commerce.models import Order
from app.modules.commerce.orders import owned_order
from app.modules.commerce.service import order_event, release_stock

router = APIRouter(tags=["Optional hosted payments"])


def stripe_client():
    settings = get_settings()
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(503, "Hosted payments are not configured; choose cash on delivery")
    return stripe.StripeClient(settings.stripe_secret_key, max_network_retries=1)


@router.post("/orders/{order_id}/payment-session")
def payment_session(order_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    order = owned_order(db, order_id, user, True)
    if (
        order.payment_method != "stripe"
        or order.status != "placed"
        or order.payment_status != "pending"
    ):
        raise HTTPException(409, "This order does not need a payment session")
    client = stripe_client()
    settings = get_settings()
    try:
        if order.stripe_session_id:
            session = client.v1.checkout.sessions.retrieve(order.stripe_session_id)
        else:
            session = client.v1.checkout.sessions.create(
                {
                    "mode": "payment",
                    "customer_email": user.email,
                    "client_reference_id": order.id,
                    "metadata": {"order_id": order.id},
                    "success_url": f"{settings.storefront_url}/#/orders/{order.id}?payment=return",
                    "cancel_url": f"{settings.storefront_url}/#/orders/{order.id}?payment=cancel",
                    "expires_at": int((datetime.now(UTC) + timedelta(minutes=31)).timestamp()),
                    "line_items": [
                        {
                            "price_data": {
                                "currency": order.currency.lower(),
                                "unit_amount": order.total_minor,
                                "product_data": {"name": f"Ayna order {order.number}"},
                            },
                            "quantity": 1,
                        }
                    ],
                },
                options={"idempotency_key": f"ayna-checkout-{order.id}"},
            )
            order.stripe_session_id = session.id
            db.commit()
    except stripe.StripeError as exc:
        raise HTTPException(
            502, "Payment provider unavailable; your order remains in your account"
        ) from exc
    if not session.url:
        raise HTTPException(409, "This payment session is no longer open; check your order status")
    return {"url": session.url}


@router.post("/payments/stripe/webhook")
async def webhook(request: Request, db=Depends(get_db)):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(503, "Webhook is not configured")
    payload = await request.body()
    if len(payload) > 1_000_000:
        raise HTTPException(413, "Webhook payload too large")
    try:
        event = stripe.Webhook.construct_event(
            payload,
            request.headers.get("stripe-signature", ""),
            settings.stripe_webhook_secret,
            tolerance=300,
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid webhook signature or payload") from exc
    kind = event["type"]
    obj = json.loads(payload)["data"]["object"]
    if kind not in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.expired",
        "checkout.session.async_payment_failed",
    }:
        return {"received": True}
    order_id = obj.get("metadata", {}).get("order_id")
    if not order_id:
        return {"received": True}
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None or order.payment_method != "stripe":
        return {"received": True}
    if order.stripe_session_id and order.stripe_session_id != obj["id"]:
        raise HTTPException(409, "Payment session does not match")
    if (
        obj.get("amount_total") != order.total_minor
        or obj.get("currency", "").upper() != order.currency
    ):
        raise HTTPException(409, "Payment amount or currency does not match")
    if kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        if obj.get("payment_status") == "paid" and order.payment_status != "paid":
            if order.stock_released or order.status == "cancelled":
                raise HTTPException(409, "Payment requires manual reconciliation")
            order.payment_status = "paid"
            order.stripe_session_id = obj["id"]
            order.stripe_payment_id = obj.get("payment_intent")
            order_event(db, order, "Payment confirmed by the payment provider.")
    elif order.payment_status == "pending" and order.status == "placed":
        release_stock(db, order)
        order.status, order.payment_status = "cancelled", "failed"
        order_event(db, order, "Payment expired or failed; inventory restored.")
    db.commit()
    return {"received": True}


def refund_hosted(order: Order):
    if not order.stripe_payment_id:
        raise HTTPException(409, "No confirmed provider payment is recorded")
    try:
        return stripe_client().v1.refunds.create(
            {"payment_intent": order.stripe_payment_id},
            options={"idempotency_key": f"ayna-refund-{order.id}"},
        )
    except stripe.StripeError as exc:
        raise HTTPException(502, "The payment provider could not process this refund") from exc
