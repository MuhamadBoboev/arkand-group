"""Единые справочники (§7.5): businesses, контрагенты, номенклатура, единицы."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize, serialize_list
from app.core.constants import Action, Resource
from app.core.deps import get_principal
from app.db.base import get_db
from app.db.models import BusinessEntity, Counterparty, Nomenclature, Unit, User
from app.schemas import CounterpartyIn, NomenclatureIn, UnitIn
from app.services.audit import write_audit
from app.services.rbac import Principal

router = APIRouter(tags=["references"])


@router.get("/businesses")
def list_businesses(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    return serialize_list(db.query(BusinessEntity).order_by(BusinessEntity.name).all())


@router.get("/users")
def list_users(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    # Список пользователей для назначения задач/доступов: владельцы (в т.ч. Довуд) или право employee.view
    if not principal.is_owner:
        principal.require(Resource.EMPLOYEE, Action.VIEW)
    return serialize_list(db.query(User).order_by(User.full_name).all())


# ---------- Контрагенты (один контрагент = одна карточка §7.5) ----------
@router.get("/counterparties")
def list_counterparties(
    q: str | None = Query(default=None),
    page: int = 1,
    size: int = 50,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    principal.require(Resource.COUNTERPARTY, Action.VIEW)
    query = db.query(Counterparty)
    if q:
        query = query.filter(Counterparty.name.ilike(f"%{q}%"))
    return paginate(query.order_by(Counterparty.name), page, size)


@router.post("/counterparties", status_code=201)
def create_counterparty(data: CounterpartyIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.COUNTERPARTY, Action.CREATE)
    existing = db.query(Counterparty).filter(Counterparty.name == data.name).first()
    if existing:
        return serialize(existing)  # один контрагент = одна карточка
    cp = Counterparty(**data.model_dump(), created_by=principal.id)
    db.add(cp)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="counterparty", ref_id=cp.id, after=data.model_dump())
    db.commit()
    db.refresh(cp)
    return serialize(cp)


# ---------- Номенклатура ----------
@router.get("/nomenclature")
def list_nomenclature(page: int = 1, size: int = 100, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.NOMENCLATURE, Action.VIEW)
    return paginate(db.query(Nomenclature).order_by(Nomenclature.name), page, size)


@router.post("/nomenclature", status_code=201)
def create_nomenclature(data: NomenclatureIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.NOMENCLATURE, Action.CREATE)
    nm = Nomenclature(**data.model_dump(), created_by=principal.id)
    db.add(nm)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="nomenclature", ref_id=nm.id, after=data.model_dump())
    db.commit()
    db.refresh(nm)
    return serialize(nm)


# ---------- Единицы измерения ----------
@router.get("/units")
def list_units(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    return serialize_list(db.query(Unit).order_by(Unit.code).all())


@router.post("/units", status_code=201)
def create_unit(data: UnitIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.NOMENCLATURE, Action.CREATE)
    u = Unit(**data.model_dump())
    db.add(u)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="nomenclature", ref_id=u.id, after=data.model_dump())
    db.commit()
    db.refresh(u)
    return serialize(u)
