"""Застройщик (§9.1): объекты, сметы (заморожены), инвентаризация, прибыль по объекту."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api._common import serialize_list
from app.api._crud import make_crud_router
from app.core.constants import Action, Resource
from app.core.deps import get_principal
from app.core.errors import not_found
from app.db.base import get_db
from app.db.models import ConstructionObject, Estimate, Inventory, WarehouseStock
from app.services.rbac import Principal

router = APIRouter(prefix="/zastroyshchik", tags=["zastroyshchik"])

router.include_router(make_crud_router(model=ConstructionObject, resource=Resource.OBJECT, tags=["zastroyshchik"]), prefix="/objects")
router.include_router(make_crud_router(model=Estimate, resource=Resource.OBJECT, tags=["zastroyshchik"], business_scoped=False), prefix="/estimates")
router.include_router(make_crud_router(model=Inventory, resource=Resource.OBJECT, tags=["zastroyshchik"]), prefix="/inventories")


@router.get("/objects/{object_id}/profit")
def object_profit(object_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """Прибыль по объекту: план/факт сметы (§9.1)."""
    obj = db.query(ConstructionObject).filter(ConstructionObject.id == object_id).first()
    if obj is None:
        raise not_found("Объект не найден")
    principal.require(Resource.OBJECT, Action.VIEW, business_id=obj.business_id)
    estimates = db.query(Estimate).filter(Estimate.object_id == object_id).all()
    plan = sum((Decimal(e.plan_amount or 0) for e in estimates), Decimal(0))
    fact = sum((Decimal(e.fact_amount or 0) for e in estimates), Decimal(0))
    return {"object_id": object_id, "plan": str(plan), "fact": str(fact), "profit": str(plan - fact)}


@router.get("/stock")
def stock(business_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.WAREHOUSE, Action.VIEW, business_id=business_id)
    return serialize_list(db.query(WarehouseStock).filter(WarehouseStock.business_id == business_id).all())
