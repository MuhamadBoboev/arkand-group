"""Движок БД, сессии, базовые миксины. Portable: Postgres (prod) + SQLite (dev/test)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UUIDPk:
    """Первичный ключ uuid (портируемо между Postgres и SQLite)."""
    id = Column(String(36), primary_key=True, default=new_id)


class Timestamped:
    """created_at / created_by — есть у всех значимых таблиц (§10)."""
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False, index=True)
    created_by = Column(String(36), nullable=True, index=True)


def get_db():
    """FastAPI-зависимость: сессия на запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
