import hashlib
import hmac
import io
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.common.config import get_settings
from app.common.db import SessionLocal
from app.common.models import Product, ProductImage
from app.common.storage import get_storage
from app.main import app
from app.modules.commerce.models import Coupon, Order, User, Variant

ORIGIN = {"Origin": "http://localhost:5173"}
ADDRESS = {
    "recipient": "Ayna Buyer",
    "phone": "+8801700000000",
    "street": "12 Sample Road",
    "city": "Dhaka",
    "postal_code": "1207",
    "country": "BD",
}


def account(client, role="customer", prefix="test"):
    client.headers.update(ORIGIN)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{prefix}-{uuid4().hex[:8]}@example.com",
            "name": f"{role.title()} Account",
            "password": "TestingPassword2026!",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def product(seller_id, stock=10, price=100000, category="bags", variants=False):
    image = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(image, "PNG")
    with SessionLocal() as db:
        p = Product(
            seller_id=seller_id,
            name="Test everyday bag",
            category=category,
            description="A useful everyday product",
            price_minor=price,
            stock=stock,
            sku=f"TEST-{uuid4().hex}",
            is_listed=True,
        )
        db.add(p)
        db.flush()
        key = f"test/{p.id}/photo.png"
        get_storage().put(key, image.getvalue(), "image/png")
        p.images.append(
            ProductImage(
                storage_key=key,
                original_key=f"test/{p.id}/original",
                view_tag="front",
                sort_order=0,
            )
        )
        option = None
        if variants:
            option = Variant(
                product_id=p.id,
                label="M / green",
                sku=f"V-{uuid4().hex}",
                stock=stock,
                price_minor=price,
                size="M",
                color="Green",
            )
            db.add(option)
        db.commit()
        return p.id, option.id if option else None


def admin(client):
    user = account(client)
    with SessionLocal() as db:
        db.get(User, user["id"]).role = "admin"
        db.commit()
    return user


def add(client, pid, qty=1, variant=None):
    response = client.post(
        "/api/v1/cart/items", json={"product_id": pid, "variant_id": variant, "quantity": qty}
    )
    assert response.status_code == 200, response.text
    return response.json()


def checkout(client, key=None, method="cod", coupon=""):
    return client.post(
        "/api/v1/checkout",
        headers={"Idempotency-Key": key or str(uuid4())},
        json={"address": ADDRESS, "payment_method": method, "coupon_code": coupon},
    )


def test_register_login_logout_password_and_csrf(client):
    user = account(client)
    assert client.get("/api/v1/auth/me").json()["id"] == user["id"]
    assert "HttpOnly" in client.cookies.get("ayna_session", "") or client.cookies.get(
        "ayna_session"
    )
    assert (
        client.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/account/password",
            json={"current_password": "bad", "new_password": "NewPassword2026!"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/account/password",
            json={"current_password": "TestingPassword2026!", "new_password": "NewPassword2026!"},
        ).status_code
        == 200
    )
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user["email"], "password": "NewPassword2026!"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "name": "Admin",
                "password": "TestingPassword2026!",
                "role": "admin",
            },
        ).status_code
        == 422
    )
    assert client.get("/api/v1/admin/users").status_code == 403


def test_session_cookie_is_httponly_and_password_hash_is_not_plaintext(client):
    user = account(client)
    response = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": "TestingPassword2026!"}
    )
    assert (
        "HttpOnly" in response.headers["set-cookie"]
        and "SameSite=lax" in response.headers["set-cookie"]
    )
    with SessionLocal() as db:
        stored = db.get(User, user["id"]).password_hash
        assert stored.startswith("scrypt$") and "TestingPassword" not in stored
    no_origin = TestClient(app)
    no_origin.cookies.update(client.cookies)
    assert no_origin.patch("/api/v1/account", json={"name": "Someone Else"}).status_code == 403


def test_guest_cart_merges_into_account_and_is_private(client):
    pid, _ = product(str(uuid4()))
    client.headers.update(ORIGIN)
    cart = add(client, pid, 2)
    assert checkout(client).status_code == 401
    other = TestClient(app, headers=ORIGIN)
    assert other.get("/api/v1/cart").json()["items"] == []
    account(client)
    merged = client.get("/api/v1/cart").json()
    assert merged["items"][0]["quantity"] == 2
    assert (
        client.patch(
            f"/api/v1/cart/items/{cart['items'][0]['id']}", json={"quantity": 3}
        ).status_code
        == 200
    )
    assert other.delete(f"/api/v1/cart/items/{cart['items'][0]['id']}").status_code == 404


def test_bdt_cod_checkout_discount_idempotency_cancel_restock(client):
    user = account(client)
    pid, _ = product(str(uuid4()), stock=5, price=100000)
    with SessionLocal() as db:
        db.add(Coupon(code="TEN", discount_percent=10, max_uses=1))
        db.commit()
    add(client, pid, 2)
    quote = client.post("/api/v1/cart/quote", json={"coupon_code": "TEN"}).json()
    assert quote["subtotal_minor"] == 200000 and quote["discount_minor"] == 20000
    assert quote["shipping_minor"] == 8000 and quote["total_minor"] == 188000
    response = checkout(client, "same-request-key", coupon="TEN")
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["currency"] == "BDT" and order["payment_status"] == "pending"
    assert checkout(client, "same-request-key", coupon="TEN").json()["id"] == order["id"]
    assert client.get("/api/v1/cart").json()["items"] == []
    with SessionLocal() as db:
        assert db.get(Product, pid).stock == 3 and db.get(Coupon, "TEN").used_count == 1
        assert len(db.scalars(select(Order).where(Order.user_id == user["id"])).all()) == 1
    stranger = TestClient(app, headers=ORIGIN)
    account(stranger)
    assert stranger.get(f"/api/v1/orders/{order['id']}").status_code == 404
    assert stranger.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 404
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 200
    assert client.post(f"/api/v1/orders/{order['id']}/cancel").status_code == 200
    with SessionLocal() as db:
        assert db.get(Product, pid).stock == 5 and db.get(Coupon, "TEN").used_count == 0


def test_checkout_rechecks_stock_and_client_cannot_choose_price(client):
    account(client)
    pid, _ = product(str(uuid4()), stock=1, price=100000)
    add(client, pid)
    with SessionLocal() as db:
        db.get(Product, pid).stock = 0
        db.commit()
    assert checkout(client).status_code == 409
    with SessionLocal() as db:
        db.get(Product, pid).stock = 1
        db.get(Product, pid).price_minor = 123400
        db.commit()
    order = checkout(client).json()
    assert order["subtotal_minor"] == 123400
    assert order["items"][0]["unit_price_minor"] == 123400


def test_variants_require_selection_and_deactivated_options_stay_unavailable(client):
    account(client)
    pid, option = product(str(uuid4()), variants=True, category="shirts", stock=2)
    assert (
        client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 1}).status_code
        == 422
    )
    add(client, pid, 2, option)
    assert checkout(client).status_code == 201
    with SessionLocal() as db:
        assert db.get(Variant, option).stock == 0
        db.get(Variant, option).is_active = False
        db.commit()
    assert client.get(f"/api/v1/shop/products/{pid}").json()["stock"] == 0
    assert (
        client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 1}).status_code
        == 422
    )


def test_listing_search_filter_archive_and_no_3d_requirement(client):
    user = account(client, "seller")
    pid, _ = product(user["id"], price=99900)
    result = client.get("/api/v1/shop/products?q=everyday&category=bags&max_price=100000").json()
    assert result["total"] == 1 and result["items"][0]["model_asset_url"] is None
    assert client.get(f"/api/v1/shop/products/{pid}/model").status_code == 404
    assert client.get("/api/v1/shop/products?max_price=100").json()["total"] == 0
    assert client.get("/api/v1/shop/products?q=%25").json()["total"] == 0
    stranger = TestClient(app, headers=ORIGIN)
    account(stranger, "seller")
    assert stranger.delete(f"/api/v1/seller/products/{pid}").status_code == 404
    assert client.delete(f"/api/v1/seller/products/{pid}").status_code == 200
    assert client.get(f"/api/v1/shop/products/{pid}").status_code == 404


def test_fulfillment_review_return_and_cod_collection(client):
    seller = TestClient(app, headers=ORIGIN)
    seller_user = account(seller, "seller")
    pid, _ = product(seller_user["id"])
    account(client)
    assert (
        client.post(
            f"/api/v1/shop/products/{pid}/reviews",
            json={"rating": 5, "title": "Good", "body": "Really useful"},
        ).status_code
        == 403
    )
    add(client, pid)
    order = checkout(client).json()
    item_id = order["items"][0]["id"]
    assert (
        client.post(
            f"/api/v1/seller/order-items/{item_id}/fulfill", json={"status": "processing"}
        ).status_code
        == 403
    )
    assert (
        seller.post(
            f"/api/v1/seller/order-items/{item_id}/fulfill", json={"status": "delivered"}
        ).status_code
        == 409
    )
    for status in ["processing", "shipped", "delivered"]:
        result = seller.post(
            f"/api/v1/seller/order-items/{item_id}/fulfill",
            json={"status": status, "tracking_number": "AY-TRACK-1", "courier": "Local"},
        )
        assert result.status_code == 200, result.text
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "delivered"
    assert (
        client.post(
            f"/api/v1/shop/products/{pid}/reviews",
            json={"rating": 5, "title": "Lovely", "body": "A really good purchase"},
        ).status_code
        == 201
    )
    assert client.get(f"/api/v1/shop/products/{pid}").json()["rating"] == 5
    assert (
        client.post(
            f"/api/v1/orders/{order['id']}/return", json={"reason": "Size is incorrect"}
        ).status_code
        == 200
    )
    manager = TestClient(app, headers=ORIGIN)
    admin(manager)
    assert (
        manager.post(
            f"/api/v1/admin/orders/{order['id']}", json={"action": "approve_return"}
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.get(Product, pid).stock == 10
    assert client.get("/api/v1/notifications").json()


def test_sellers_cannot_read_other_sellers_order_items(client):
    a, b = TestClient(app, headers=ORIGIN), TestClient(app, headers=ORIGIN)
    one, two = account(a, "seller"), account(b, "seller")
    pid, _ = product(one["id"], price=10000)
    other_pid, _ = product(two["id"], price=900000)
    account(client)
    add(client, pid)
    add(client, other_pid)
    checkout(client)
    visible = a.get("/api/v1/seller/orders").json()[0]
    assert len(visible["items"]) == 1 and visible["items"][0]["product_id"] == pid
    assert visible["total_minor"] == 10000 and visible["events"] == []


def test_addresses_wishlist_support_and_admin_response(client):
    account(client)
    pid, _ = product(str(uuid4()))
    assert client.put(f"/api/v1/wishlist/{pid}").status_code == 200
    assert len(client.get("/api/v1/wishlist").json()) == 1
    address = client.post("/api/v1/account/addresses", json=ADDRESS).json()
    ticket = client.post(
        "/api/v1/support/tickets",
        json={"subject": "Delivery help", "message": "Please help me with delivery options"},
    ).json()
    manager = TestClient(app, headers=ORIGIN)
    admin(manager)
    assert (
        manager.post(
            f"/api/v1/admin/tickets/{ticket['id']}/reply",
            json={"response": "Please check your order details", "status": "resolved"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/support/tickets").json()[0]["response"]
    assert manager.delete(f"/api/v1/account/addresses/{address['id']}").status_code == 404
    assert client.delete(f"/api/v1/account/addresses/{address['id']}").status_code == 200


def test_reset_link_single_use_and_account_suspension(client):
    user = account(client)
    response = client.post("/api/v1/auth/forgot-password", json={"email": user["email"]}).json()
    token = response["development_reset_url"].split("token=")[1]
    assert (
        client.post(
            "/api/v1/auth/reset-password", json={"token": token, "password": "ChangedPassword2026!"}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/reset-password", json={"token": token, "password": "ChangedPassword2026!"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user["email"], "password": "ChangedPassword2026!"}
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        db.get(User, user["id"]).is_active = False
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_coupon_limit_and_unconfigured_payment_fail_closed(client):
    account(client)
    pid, _ = product(str(uuid4()))
    add(client, pid)
    assert checkout(client, method="stripe").status_code == 422
    assert client.post("/api/v1/cart/quote", json={"coupon_code": "FAKE"}).status_code == 422
    with SessionLocal() as db:
        db.add(Coupon(code="USED", max_uses=1, used_count=1, discount_percent=10))
        db.commit()
    assert checkout(client, coupon="USED").status_code == 422
    assert client.post("/api/v1/payments/stripe/webhook", content=b"{}").status_code == 503


def test_stripe_webhook_signature_amount_and_replay_are_checked(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "test-placeholder")
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", "webhook-placeholder")
    account(client)
    pid, _ = product(str(uuid4()))
    add(client, pid)
    order = checkout(client, method="stripe").json()
    obj = {
        "id": "cs_example",
        "metadata": {"order_id": order["id"]},
        "payment_status": "paid",
        "amount_total": order["total_minor"],
        "currency": "bdt",
        "payment_intent": "pi_example",
    }

    def send(amount):
        obj["amount_total"] = amount
        raw = json.dumps(
            {"id": "evt_example", "type": "checkout.session.completed", "data": {"object": obj}}
        ).encode()
        stamp = int(time.time())
        signature = hmac.new(
            b"webhook-placeholder", str(stamp).encode() + b"." + raw, hashlib.sha256
        ).hexdigest()
        return client.post(
            "/api/v1/payments/stripe/webhook",
            content=raw,
            headers={"Stripe-Signature": f"t={stamp},v1={signature}"},
        )

    assert client.post("/api/v1/payments/stripe/webhook", content=b"{}").status_code == 400
    assert send(order["total_minor"] - 1).status_code == 409
    assert send(order["total_minor"]).status_code == 200
    assert send(order["total_minor"]).status_code == 200
    with SessionLocal() as db:
        assert db.get(Order, order["id"]).payment_status == "paid"
        assert db.get(Product, pid).stock == 9


def test_admin_settings_coupon_and_category_management(client):
    user = admin(client)
    assert (
        client.patch(
            f"/api/v1/admin/users/{user['id']}", json={"role": "admin", "is_active": True}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").status_code == 200
    assert (
        client.patch(
            f"/api/v1/admin/users/{user['id']}", json={"role": "customer", "is_active": False}
        ).status_code
        == 409
    )
    assert (
        client.put("/api/v1/admin/categories/art", json={"slug": "art", "name": "Art"}).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/admin/coupons/HELLO", json={"code": "hello", "discount_percent": 20}
        ).status_code
        == 200
    )
    config = client.get("/api/v1/shop/config").json()
    settings = {
        key: config[key]
        for key in [
            "name",
            "tagline",
            "shipping_minor",
            "free_shipping_minor",
            "tax_basis_points",
            "support_email",
            "announcement",
        ]
    }
    settings["shipping_minor"] = 5000
    assert client.put("/api/v1/admin/settings", json=settings).json()["shipping_minor"] == 5000
    assert (
        client.put(
            "/api/v1/admin/categories/art",
            json={"slug": "art", "name": "Art", "is_active": False},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/shop/config").json()["categories"] == []
