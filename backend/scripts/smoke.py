"""Run against the live Compose API + worker + PostgreSQL + MinIO (no provider calls)."""

import io
import os
import time
from uuid import uuid4

import httpx
from PIL import Image


def main():
    base = os.environ.get("SMOKE_API_URL", "http://localhost:8000")
    image = io.BytesIO()
    Image.new("RGB", (96, 96), (196, 142, 87)).save(image, "PNG")
    with httpx.Client(base_url=base, timeout=20) as client:
        assert client.get("/ready").status_code == 200
        assert client.get("/api/v1/config").json()["provider"] == "mock"
        for count, decision in [(2, "approve"), (5, "reject")]:
            owner = {"X-Dev-Seller-Id": str(uuid4())}
            response = client.post(
                "/api/v1/products",
                headers=owner,
                json={
                    "name": f"Ayna smoke {count} photos",
                    "category": "bags",
                },
            )
            response.raise_for_status()
            product_id = response.json()["id"]
            path = f"/api/v1/products/{product_id}"
            assert client.get(f"/api/v1/store/products/{product_id}").status_code == 404
            response = client.post(
                path + "/images",
                headers=owner,
                files=[
                    ("files", (f"view-{i}.png", image.getvalue(), "image/png"))
                    for i in range(count)
                ],
            )
            response.raise_for_status()
            assert len(response.json()["images"]) == count
            assert client.post(
                path + "/images", headers=owner, files={"files": ("bad.png", b"bad", "image/png")}
            ).status_code in {422}
            headers = {**owner, "Idempotency-Key": str(uuid4())}
            response = client.post(path + "/generation-jobs", headers=headers)
            assert response.status_code == 202, response.text
            job_id = response.json()["id"]
            assert client.post(path + "/generation-jobs", headers=headers).json()["id"] == job_id
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                job = client.get(f"/api/v1/generation-jobs/{job_id}", headers=owner).json()
                if job["status"] in {"succeeded", "failed", "cancelled"}:
                    break
                time.sleep(0.3)
            assert job["status"] == "succeeded", job
            assert client.get(job["model_asset_url"]).content.startswith(b"glTF")
            quality = client.get(path + "/quality", headers=owner).json()
            assert quality["status"] == "not_evaluated" and quality["metrics"] == {}
            assert (
                client.post(
                    path + "/review",
                    headers={"X-Dev-Seller-Id": str(uuid4())},
                    json={"decision": "approve"},
                ).status_code
                == 404
            )
            assert (
                client.post(
                    path + "/review",
                    headers=owner,
                    json={"decision": decision, "notes": "Mock smoke test"},
                ).status_code
                == 200
            )
            public = client.get(f"/api/v1/store/products/{product_id}")
            assert public.status_code == (200 if decision == "approve" else 404)
            if decision == "approve":
                assert client.get(public.json()["model_asset_url"]).content.startswith(b"glTF")
                # Leave no published smoke artifacts behind.
                client.post(
                    path + "/review", headers=owner, json={"decision": "reject"}
                ).raise_for_status()
                assert client.get(public.json()["model_asset_url"]).status_code == 404
            print(f"PASS: {count} photos → RQ → stored dummy GLB → honest quality → {decision}")
    print("Ayna live mock smoke passed; no GPU, cloud credentials, or paid provider requests.")


if __name__ == "__main__":
    main()
