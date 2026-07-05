"""ARKAND CRM — точка входа FastAPI (§2, §11, §12)."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.ws import router as ws_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.db import models  # noqa: F401 — регистрация таблиц в metadata
from app.db.base import Base, engine
from app.realtime.publisher import init_publisher, shutdown_publisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # dev-удобство: создать таблицы (в проде — Alembic, §2)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    # авто-сид демо-данных при первом старте (для деплоя) — идемпотентно
    if settings.seed_on_start:
        try:
            from app.seed import ensure_demo_data, ensure_demo_users, run as seed_run

            seed_run()
            ensure_demo_users()  # идемпотентная дозаливка недостающих демо-пользователей
            ensure_demo_data()   # насыщение демо-данными всех систем (по пустым категориям)
        except Exception as exc:  # сид не должен ронять старт
            print("seed_on_start failed:", exc)
    await init_publisher(asyncio.get_running_loop())
    yield
    await shutdown_publisher()


app = FastAPI(
    title="ARKAND · Финансовая CRM холдинга",
    version="1.0.0",
    description="Единая CRM-экосистема строительного холдинга. Реализация строго по ТЗ.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/", tags=["system"])
def root():
    return {
        "app": "ARKAND · Финансовая CRM холдинга",
        "docs": "/docs",
        "health": "/health",
        "brand": "webrand.tj · +992 988 64 55 43",
    }
