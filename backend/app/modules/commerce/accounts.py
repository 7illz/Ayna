import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.common.config import get_settings
from app.common.db import get_db
from app.common.identity import (
    COOKIE,
    aware,
    create_session,
    current_user,
    digest,
    merge_guest_cart,
    password_hash,
    revoke_sessions,
    throttle,
    verify_password,
)
from app.common.mail import send_reset
from app.modules.commerce.models import Address, AuthSession, ResetToken, User
from app.modules.commerce.schemas import (
    AddressIn,
    AddressOut,
    ForgotIn,
    LoginIn,
    MessageOut,
    PasswordIn,
    ProfileIn,
    RegisterIn,
    ResetIn,
    UserOut,
)

router = APIRouter(tags=["Accounts"])


def auth_limit(db, request: Request, email: str):
    ip = request.client.host if request.client else "unknown"
    throttle(db, f"auth-ip:{ip}", 100)
    throttle(db, f"auth-email:{email.strip().casefold()}", 20)


@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, request: Request, response: Response, db=Depends(get_db)):
    auth_limit(db, request, body.email)
    user = User(
        email=body.email.strip().casefold(),
        name=body.name.strip(),
        role=body.role,
        password_hash=password_hash(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "An account with that email already exists") from exc
    merge_guest_cart(db, user, request, response)
    create_session(db, user, response)
    return user


@router.post("/auth/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db=Depends(get_db)):
    email = body.email.strip().casefold()
    auth_limit(db, request, email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # Equal-cost password work for unknown accounts.
        password_hash(body.password)
        raise HTTPException(401, "Email or password is incorrect")
    if not verify_password(body.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Email or password is incorrect")
    merge_guest_cart(db, user, request, response)
    create_session(db, user, response)
    return user


@router.get("/auth/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user


@router.post("/auth/logout", response_model=MessageOut)
def logout(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == digest(token)))
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return MessageOut(message="Signed out")


@router.patch("/account", response_model=UserOut)
def profile(body: ProfileIn, user=Depends(current_user), db=Depends(get_db)):
    user.name = body.name.strip()
    db.commit()
    return user


@router.post("/account/password", response_model=MessageOut)
def change_password(
    body: PasswordIn, response: Response, user=Depends(current_user), db=Depends(get_db)
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = password_hash(body.new_password)
    db.execute(update(ResetToken).where(ResetToken.user_id == user.id).values(used=True))
    revoke_sessions(db, user.id)
    create_session(db, user, response)
    return MessageOut(message="Password updated; other sessions signed out")


@router.post("/auth/forgot-password", response_model=MessageOut)
def forgot(body: ForgotIn, request: Request, db=Depends(get_db)):
    auth_limit(db, request, body.email)
    result = MessageOut(message="If that account exists, password reset instructions are available")
    user = db.scalar(select(User).where(User.email == body.email.strip().casefold()))
    settings = get_settings()
    if settings.environment == "production" and not settings.smtp_host:
        raise HTTPException(503, "Password recovery email is not configured")
    if user:
        token = secrets.token_urlsafe(48)
        db.add(
            ResetToken(
                token_hash=digest(token),
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        db.commit()
        reset_url = f"{settings.storefront_url}/#/reset-password?token={token}"
        if settings.environment in {"development", "test"}:
            result.development_reset_url = reset_url
        else:
            try:
                send_reset(user.email, reset_url)
            except Exception as exc:
                raise HTTPException(
                    503, "Recovery email could not be sent; try again later"
                ) from exc
    return result


@router.post("/auth/reset-password", response_model=MessageOut)
def reset_password(body: ResetIn, request: Request, db=Depends(get_db)):
    throttle(db, f"reset:{request.client.host if request.client else 'unknown'}", 30)
    record = db.scalar(
        select(ResetToken).where(ResetToken.token_hash == digest(body.token)).with_for_update()
    )
    if record is None or record.used or aware(record.expires_at) <= datetime.now(UTC):
        raise HTTPException(400, "Reset link is invalid or expired")
    user = db.get(User, record.user_id)
    user.password_hash = password_hash(body.password)
    record.used = True
    db.execute(update(ResetToken).where(ResetToken.user_id == user.id).values(used=True))
    revoke_sessions(db, user.id)
    db.commit()
    return MessageOut(message="Password reset. Sign in with your new password.")


@router.get("/account/addresses", response_model=list[AddressOut])
def addresses(user=Depends(current_user), db=Depends(get_db)):
    return db.scalars(select(Address).where(Address.user_id == user.id)).all()


@router.post("/account/addresses", response_model=AddressOut, status_code=201)
def add_address(body: AddressIn, user=Depends(current_user), db=Depends(get_db)):
    if len(db.scalars(select(Address.id).where(Address.user_id == user.id)).all()) >= 20:
        raise HTTPException(422, "Address book limit reached")
    address = Address(user_id=user.id, **body.model_dump())
    db.add(address)
    db.commit()
    return address


@router.delete("/account/addresses/{address_id}", response_model=MessageOut)
def delete_address(address_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    address = db.get(Address, str(address_id))
    if address is None or address.user_id != user.id:
        raise HTTPException(404, "Address not found")
    db.delete(address)
    db.commit()
    return MessageOut(message="Address removed")


@router.put("/account/addresses/{address_id}", response_model=AddressOut)
def edit_address(address_id: UUID, body: AddressIn, user=Depends(current_user), db=Depends(get_db)):
    address = db.get(Address, str(address_id))
    if address is None or address.user_id != user.id:
        raise HTTPException(404, "Address not found")
    for key, value in body.model_dump().items():
        setattr(address, key, value)
    db.commit()
    return address
