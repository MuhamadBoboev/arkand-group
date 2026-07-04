"""Щебёночный завод (§9.4): фракции, смены, выпуск, солярка, мощность, заказы, отгрузка."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api._common import serialize_list
from app.api._crud import make_crud_router
from app.api._production import make_orders_router, make_shipping_router
from app.core.constants import Action, Business, Resource
from app.core.deps import get_principal
from app.db.base import get_db
from app.db.models import (
    CapacityRecord,
    Fraction,
    FractionOutput,
    FuelConsumption,
    ProductionShift,
    WarehouseStock,
)
from app.services.rbac import Principal

router = APIRouter(prefix="/shcheben", tags=["shcheben"])

_F = Resource.FRACTION
router.include_router(make_orders_router(Business.SHCHEBEN), prefix="/orders")
router.include_router(make_shipping_router(Business.SHCHEBEN), prefix="/shipping")
router.include_router(make_crud_router(model=Fraction, resource=_F, tags=["shcheben"]), prefix="/fractions")
router.include_router(make_crud_router(model=ProductionShift, resource=_F, tags=["shcheben"]), prefix="/shifts")
router.include_router(make_crud_router(model=FractionOutput, resource=_F, tags=["shcheben"], business_scoped=False), prefix="/outputs")
router.include_router(make_crud_router(model=FuelConsumption, resource=_F, tags=["shcheben"]), prefix="/fuel")
router.include_router(make_crud_router(model=CapacityRecord, resource=_F, tags=["shcheben"]), prefix="/capacity")


@router.get("/stock")
def stock(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.WAREHOUSE, Action.VIEW, business_id=Business.SHCHEBEN)
    return serialize_list(db.query(WarehouseStock).filter(WarehouseStock.business_id == Business.SHCHEBEN).all())
