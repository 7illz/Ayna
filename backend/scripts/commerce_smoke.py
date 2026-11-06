"""Exercise the live API and its transaction semantics without making paid requests."""

import io
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
from PIL import Image

from app.common.config import get_settings


def main():
    base = os.environ.get("SMOKE_API_URL", "http://localhost:8000")
    origin = get_settings().storefront_url
    clients = [
        httpx.Client(base_url=base, headers={"Origin": origin}, timeout=20) for _ in range(3)
    ]
    try:
        seller, buyer_a, buyer_b = clients
        for index, client in enumerate(clients):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"smoke-{uuid4().hex}@example.com",
                    "name": f"Commerce smoke {index}",
                    "password": "SmokePassword2026!",
                    "role": "seller" if index == 0 else "customer",
                },
            )
            response.raise_for_status()
        listing = {
            "name": "Commerce transaction smoke fixture",
            "category": "bags",
            "description": "CC0 procedural test image; not for actual sale",
            "brand": "Test fixture",
            "sku": f"SMOKE-{uuid4().hex}",
            "price_minor": 10000,
            "stock": 1,
            "is_listed": False,
        }
        response = seller.post("/api/v1/seller/products", json=listing)
        response.raise_for_status()
        product_id = response.json()["id"]
        image = io.BytesIO()
        Image.new("RGB", (48, 48), "olive").save(image, "PNG")
        seller.post(
            f"/api/v1/seller/products/{product_id}/images",
            files={"files": ("test.png", image.getvalue(), "image/png")},
        ).raise_for_status()
        listing["is_listed"] = True
        seller.put(f"/api/v1/seller/products/{product_id}", json=listing).raise_for_status()
        for buyer in [buyer_a, buyer_b]:
            buyer.post(
                "/api/v1/cart/items", json={"product_id": product_id, "quantity": 1}
            ).raise_for_status()
        body = {
            "payment_method": "cod",
            "address": {
                "recipient": "Smoke Customer",
                "phone": "+8801700000000",
                "street": "12 Sample Road",
                "city": "Dhaka",
                "postal_code": "1207",
                "country": "BD",
            },
        }

        def place(buyer):
            return buyer.post(
                "/api/v1/checkout", json=body, headers={"Idempotency-Key": str(uuid4())}
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(place, [buyer_a, buyer_b]))
        assert sorted(r.status_code for r in results) == [201, 409], [r.text for r in results]
        index = next(i for i, r in enumerate(results) if r.status_code == 201)
        winning_buyer = [buyer_a, buyer_b][index]
        order = results[index].json()
        assert order["items"][0]["unit_price_minor"] == 10000
        assert winning_buyer.get(f"/api/v1/orders/{order['id']}").status_code == 200
        assert [buyer_a, buyer_b][1 - index].get(f"/api/v1/orders/{order['id']}").status_code == 404
        winning_buyer.post(f"/api/v1/orders/{order['id']}/cancel").raise_for_status()
        assert seller.get("/api/v1/seller/products").json()[0]["stock"] == 1
        seller.delete(f"/api/v1/seller/products/{product_id}").raise_for_status()
        print(
            "PASS: photo listing, concurrent stock reservation, COD, "
            "private order, cancellation/restock"
        )
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
