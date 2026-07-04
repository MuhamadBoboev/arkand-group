"""Бетонный завод (§9.3): заказы (заморозка рецептуры, автосписание), рецептуры,
отгрузка (талон, ≠ касса), контроль качества, склад сырья."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api._common import serialize_list
from app.api._crud import make_crud_router
from app.api._production import make_orders_router, make_shipping_router
from app.core.constants import Action, Business, Resource
from app.core.deps import get_principal
from app.db.base import get_db
from app.db.models import QualityPass, Recipe, WarehouseStock
from app.services.rbac import Principal

router = APIRouter(prefix="/beton", tags=["beton"])

router.include_router(make_orders_router(Business.BETON), prefix="/orders")
router.include_router(make_shipping_router(Business.BETON), prefix="/shipping")
router.include_router(make_crud_router(model=Recipe, resource=Resource.RECIPE, tags=["beton"]), prefix="/recipes")
router.include_router(make_crud_router(model=QualityPass, resource=Resource.QUALITY, tags=["beton"]), prefix="/quality")


@router.get("/stock")
def stock(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.WAREHOUSE, Action.VIEW, business_id=Business.BETON)
    return serialize_list(db.query(WarehouseStock).filter(WarehouseStock.business_id == Business.BETON).all())
