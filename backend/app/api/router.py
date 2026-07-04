"""Агрегатор REST-роутеров под /api."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    audit_dept,
    auth,
    beton,
    finance,
    inkassaciya,
    owners,
    proektnaya,
    references,
    shcheben,
    supply,
    zastroyshchik,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(references.router)
api_router.include_router(finance.router)
api_router.include_router(inkassaciya.router)
api_router.include_router(supply.router)
api_router.include_router(owners.router)
api_router.include_router(audit_dept.router)
api_router.include_router(zastroyshchik.router)
api_router.include_router(proektnaya.router)
api_router.include_router(beton.router)
api_router.include_router(shcheben.router)
