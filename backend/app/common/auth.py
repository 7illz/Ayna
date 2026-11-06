from uuid import UUID

from fastapi import Depends, Header, HTTPException

from app.common.config import get_settings
from app.common.identity import optional_user


def seller_id(
    x_dev_seller_id: UUID | None = Header(default=None), user=Depends(optional_user)
) -> str:
    if user is not None:
        if user.role not in {"seller", "admin"}:
            raise HTTPException(403, "A seller account is required")
        return user.id
    settings = get_settings()
    if not settings.dev_auth_enabled or settings.environment == "production":
        raise HTTPException(503, "Seller authentication is not configured")
    if x_dev_seller_id is None:
        raise HTTPException(401, "Development seller header is required")
    return str(x_dev_seller_id)
