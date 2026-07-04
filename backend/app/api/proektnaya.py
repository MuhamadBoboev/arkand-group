"""Проектная компания (§9.2): клиенты, брифы, договоры (50/30/20), проекты, этапы,
авторский надзор, геодезия. Аванс = обязательство, не выручка (§7.4)."""
from __future__ import annotations

from app.api._crud import make_crud_router
from app.core.constants import Resource
from app.db.models import (
    Brief,
    Client,
    Contract,
    GeodesyRequest,
    Project,
    Stage,
    SupervisionObject,
    SupervisionPayment,
    SupervisionRound,
)
from fastapi import APIRouter

router = APIRouter(prefix="/proektnaya", tags=["proektnaya"])

_P = Resource.PROJECT
router.include_router(make_crud_router(model=Client, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/clients")
router.include_router(make_crud_router(model=Brief, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/briefs")
router.include_router(make_crud_router(model=Contract, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/contracts")
router.include_router(make_crud_router(model=Project, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/projects")
router.include_router(make_crud_router(model=Stage, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/stages")
router.include_router(make_crud_router(model=SupervisionObject, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/supervision")
router.include_router(make_crud_router(model=SupervisionRound, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/supervision-rounds")
router.include_router(make_crud_router(model=SupervisionPayment, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/supervision-payments")
router.include_router(make_crud_router(model=GeodesyRequest, resource=_P, tags=["proektnaya"], business_scoped=False), prefix="/geodesy")
