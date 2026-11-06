import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.common.config import get_settings
from app.common.db import get_db
from app.modules.commerce.models import AuthSession, AuthThrottle, CartItem, User

COOKIE = "ayna_session"
GUEST_COOKIE = "ayna_guest_cart"


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    value = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3, maxmem=64 * 1024 * 1024
    ).hex()
    return f"scrypt${salt}${value}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3, maxmem=64 * 1024 * 1024
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def optional_user(request: Request, db=Depends(get_db)) -> User | None:
    authorization = request.headers.get("authorization", "")
    token = (
        authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get(COOKIE)
    )
    if not token:
        return None
    session = db.get(AuthSession, digest(token))
    if session is None or aware(session.expires_at) <= datetime.now(UTC):
        return None
    user = db.get(User, session.user_id)
    return user if user and user.is_active else None


def current_user(user=Depends(optional_user)) -> User:
    if user is None or user.role == "guest":
        raise HTTPException(401, "Sign in to continue")
    return user


def cart_user(
    request: Request, response: Response, user=Depends(optional_user), db=Depends(get_db)
):
    if user:
        return user
    token = request.cookies.get(GUEST_COOKIE)
    session = db.get(AuthSession, digest(token)) if token else None
    if session and aware(session.expires_at) > datetime.now(UTC):
        guest = db.get(User, session.user_id)
        if guest and guest.role == "guest":
            return guest
    throttle(db, f"guest-cart:{request.client.host if request.client else 'unknown'}", 100)
    guest = User(
        email=f"guest-{secrets.token_hex(16)}@cart.invalid",
        name="Guest",
        role="guest",
        password_hash="disabled",
    )
    db.add(guest)
    db.flush()
    token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            token_hash=digest(token),
            user_id=guest.id,
            expires_at=datetime.now(UTC) + timedelta(days=14),
        )
    )
    db.commit()
    response.set_cookie(
        GUEST_COOKIE,
        token,
        max_age=14 * 86400,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
    )
    return guest


def merge_guest_cart(db, user: User, request: Request, response: Response):
    token = request.cookies.get(GUEST_COOKIE)
    session = db.get(AuthSession, digest(token)) if token else None
    guest = db.get(User, session.user_id) if session else None
    if (
        guest
        and session
        and guest.role == "guest"
        and aware(session.expires_at) > datetime.now(UTC)
    ):
        for item in db.scalars(select(CartItem).where(CartItem.user_id == guest.id)).all():
            existing = db.scalar(
                select(CartItem).where(
                    CartItem.user_id == user.id,
                    CartItem.product_id == item.product_id,
                    CartItem.variant_key == item.variant_key,
                )
            )
            if existing:
                existing.quantity = min(99, existing.quantity + item.quantity)
                db.delete(item)
            else:
                item.user_id = user.id
        db.flush()
        db.execute(delete(AuthSession).where(AuthSession.user_id == guest.id))
        db.delete(guest)
        db.commit()
    response.delete_cookie(GUEST_COOKIE)


def seller_user(user: User = Depends(current_user)) -> User:
    if user.role not in {"seller", "admin"}:
        raise HTTPException(403, "A seller account is required")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Administrator access is required")
    return user


def create_session(db, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(48)
    settings = get_settings()
    lifetime = settings.session_days * 86400
    db.add(
        AuthSession(
            token_hash=digest(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(seconds=lifetime),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=lifetime,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path="/",
    )


def revoke_sessions(db, user_id: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))


def throttle(db, key: str, limit: int = 20) -> None:
    key_hash = digest(key)
    record = db.scalar(select(AuthThrottle).where(AuthThrottle.key == key_hash).with_for_update())
    now = datetime.now(UTC)
    if record is None:
        record = AuthThrottle(key=key_hash, count=0, started_at=now)
        db.add(record)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(429, "Please wait before trying again") from None
    if now - aware(record.started_at) > timedelta(minutes=15):
        record.count, record.started_at = 0, now
    record.count += 1
    db.commit()
    if record.count > limit:
        raise HTTPException(429, "Too many attempts; try again in 15 minutes")
