"""Auth: login (refresh → httpOnly cookie), refresh (из cookie), logout, me.

Безопасность: access-токен отдаётся в теле (клиент держит его только в памяти),
refresh-токен НЕ виден JS — только httpOnly Secure cookie.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_principal
from app.core.errors import AppError
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.base import get_db
from app.db.models import Role, User, UserRole
from app.schemas import AccessTokenOut, LoginIn, MeOut, PermissionOut
from app.services.rbac import Principal

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.eff_cookie_secure,
        samesite=settings.eff_cookie_samesite,  # type: ignore[arg-type]
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/",
        httponly=True,
        secure=settings.eff_cookie_secure,
        samesite=settings.eff_cookie_samesite,  # type: ignore[arg-type]
    )


@router.post("/login", response_model=AccessTokenOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == data.phone).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise AppError("bad_credentials", "Неверный телефон или пароль", status_code=401)
    if not user.is_active:
        raise AppError("disabled", "Доступ отключён", status_code=403)
    _set_refresh_cookie(response, create_refresh_token(user.id))
    return AccessTokenOut(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=AccessTokenOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise AppError("unauthorized", "Нет refresh-сессии", status_code=401)
    try:
        payload = decode_token(token)
    except Exception:
        raise AppError("unauthorized", "Недействительная сессия", status_code=401)
    if payload.get("type") != "refresh":
        raise AppError("unauthorized", "Недействительная сессия", status_code=401)
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None or not user.is_active:
        _clear_refresh_cookie(response)
        raise AppError("unauthorized", "Пользователь недоступен", status_code=401)
    # ротация refresh-токена
    _set_refresh_cookie(response, create_refresh_token(user.id))
    return AccessTokenOut(access_token=create_access_token(user.id))


@router.post("/logout")
def logout(response: Response):
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    role_ids = [r.role_id for r in db.query(UserRole).filter(UserRole.user_id == principal.id).all()]
    role_names = [r.name for r in db.query(Role).filter(Role.id.in_(role_ids)).all()] if role_ids else []
    return MeOut(
        id=principal.id,
        full_name=principal.user.full_name,
        phone=principal.user.phone,
        is_owner=principal.is_owner,
        owner_type=principal.owner_type,
        roles=role_names,
        permissions=[PermissionOut(resource=r, action=a, scope=s) for (r, a, s) in sorted(principal.permissions)],
        businesses=sorted(principal.businesses),
    )
