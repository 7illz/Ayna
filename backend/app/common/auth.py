from uuid import UUID

from fastapi import Header, HTTPException

from app.common.config import get_settings


def seller_id(x_dev_seller_id: UUID | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.dev_auth_enabled or settings.environment == "production":
        raise HTTPException(503, "Seller authentication is not configured")
    if x_dev_seller_id is None:
        raise HTTPException(401, "Development seller header is required")
    return str(x_dev_seller_id)
