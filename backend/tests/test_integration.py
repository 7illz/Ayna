from unittest.mock import patch

from test_workflow import OTHER, create, generate

from app.common.config import get_settings
from app.common.db import SessionLocal
from app.common.models import QualityReport


def test_integrated_api_has_no_duplicate_method_path_or_operation_id(client):
    from app.main import app

    registered = []
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/v1"):
            registered.extend((method, route.path) for method in route.methods)
    assert len(registered) == len(set(registered))
    document = client.get("/openapi.json").json()
    operations = [
        value["operationId"]
        for path in document["paths"].values()
        for value in path.values()
        if isinstance(value, dict) and "operationId" in value
    ]
    assert len(operations) == len(set(operations))


def test_photograph_reorder_ownership_front_view_and_publication_revocation(client, owner):
    product = create(client, owner, 3)
    job = generate(client, owner, product)
    path = f"/api/v1/products/{product['id']}"
    client.post(path + "/review", headers=owner, json={"decision": "approve"})
    images = [
        {"id": image["id"], "view_tag": tag}
        for image, tag in zip(reversed(product["images"]), ["front", "left", "back"], strict=True)
    ]
    assert (
        client.put(path + "/images/order", headers=OTHER, json={"images": images}).status_code
        == 404
    )
    assert (
        client.put(path + "/images/order", headers=owner, json={"images": images[:1]}).status_code
        == 422
    )
    bad = [{**image, "view_tag": "back"} for image in images]
    assert (
        client.put(path + "/images/order", headers=owner, json={"images": bad}).status_code == 422
    )
    response = client.put(path + "/images/order", headers=owner, json={"images": images})
    assert response.status_code == 200
    assert [image["id"] for image in response.json()["images"]] == [image["id"] for image in images]
    assert response.json()["publish_status"] == "draft"
    assert client.get(f"/api/v1/store/products/{product['id']}/model").status_code == 404
    with SessionLocal() as db:
        assert db.get(QualityReport, job["id"]).reviewed_by is not None


def test_quality_inspection_renders_are_signed_and_private(client, owner):
    product = create(client, owner)
    job = generate(client, owner, product)
    assert len(job["preview_asset_urls"]) == 4
    for url in job["preview_asset_urls"]:
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert client.get(url.replace("sig=", "sig=bad")).status_code == 403
    public = client.get(f"/api/v1/store/products/{product['id']}")
    assert public.status_code == 404


def test_generation_seller_cap_and_idempotent_replay(client, owner, monkeypatch):
    product = create(client, owner)
    monkeypatch.setattr(get_settings(), "generation_seller_daily_limit", 1)
    first = generate(client, owner, product)
    assert generate(client, owner, product)["id"] == first["id"]
    assert (
        client.post(
            f"/api/v1/products/{product['id']}/generation-jobs",
            headers={**owner, "Idempotency-Key": "another-request"},
        ).status_code
        == 429
    )


def test_cookie_seller_can_use_studio_when_legacy_auth_disabled(client, monkeypatch):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "studio@example.com",
            "name": "Studio Seller",
            "password": "StudioPassword!2026",
            "role": "seller",
        },
    )
    assert response.status_code == 201
    monkeypatch.setattr(get_settings(), "dev_auth_enabled", False)
    config = client.get("/api/v1/config").json()
    assert config["dev_auth_enabled"] is False and config["seller_authenticated"] is True
    assert client.get("/api/v1/products").status_code == 200


def test_repeated_review_notes_stay_bounded_with_append_only_audits(client, owner):
    product = create(client, owner)
    generate(client, owner, product)
    for decision in ["approve", "reject", "approve"]:
        response = client.post(
            f"/api/v1/products/{product['id']}/review",
            headers=owner,
            json={"decision": decision, "notes": "x" * 2000},
        )
        assert response.status_code == 200
    report = client.get(f"/api/v1/products/{product['id']}/quality", headers=owner).json()
    assert len(report["notes"]) <= 3000


def test_provider_download_is_bounded(monkeypatch):
    import httpx

    from app.modules.generation.meshy import MeshyProvider, ProviderError

    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"oversize"))
    )
    with patch("app.modules.generation.meshy.MAX_GLB_BYTES", 4):
        try:
            MeshyProvider._download(client, "https://assets.meshy.ai/model.glb")
        except ProviderError as exc:
            assert str(exc) == "PROVIDER_ASSET_TOO_LARGE"
        else:
            raise AssertionError("Oversize download accepted")
