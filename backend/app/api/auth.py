"""Auth (§8, §14): login, refresh, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_principal
from app.core.errors import AppError
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.base import get_db
from app.db.models import Role, User, UserRole
from app.schemas import LoginIn, MeOut, PermissionOut, RefreshIn, TokenOut
from app.services.rbac import Principal

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == data.phone).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise AppError("bad_credentials", "Неверный телефон или пароль", status_code=401)
    if not user.is_active:
        raise AppError("disabled", "Доступ отключён", status_code=403)
    return TokenOut(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token)
    except Exception:
        raise AppError("unauthorized", "Недействительный refresh-токен", status_code=401)
    if payload.get("type") != "refresh":
        raise AppError("unauthorized", "Ожидается refresh-токен", status_code=401)
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None or not user.is_active:
        raise AppError("unauthorized", "Пользователь недоступен", status_code=401)
    return TokenOut(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


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
