"""FastAPI-зависимости: текущий пользователь (JWT) и Principal с правами (§8, §14)."""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.base import get_db
from app.db.models import User
from app.services.rbac import Principal, build_principal

bearer = HTTPBearer(auto_error=False)


def _unauthorized(msg: str = "Требуется авторизация") -> AppError:
    return AppError("unauthorized", msg, status_code=401)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise _unauthorized()
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise _unauthorized("Недействительный токен")
    if payload.get("type") != "access":
        raise _unauthorized("Ожидается access-токен")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None:
        raise _unauthorized("Пользователь не найден")
    if not user.is_active:
        raise AppError("disabled", "Доступ отключён", status_code=403)
    return user


def get_principal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Principal:
    return build_principal(db, user)
