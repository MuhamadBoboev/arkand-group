"""Инкассация (§9.6.1, §11): start → fact → accept (другой пользователь)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize
from app.core.constants import Action, Resource
from app.core.deps import get_principal
from app.core.errors import not_found
from app.db.base import get_db
from app.db.models import CashRegister, Inkassaciya
from app.schemas import InkAcceptIn, InkFactIn, InkStartIn
from app.services import inkassaciya as ink_service
from app.services.analytics import invalidate_summary
from app.services.rbac import Principal

router = APIRouter(prefix="/inkassaciya", tags=["inkassaciya"])


@router.get("")
def list_inkassaciya(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.INKASSACIYA, Action.VIEW)
    return paginate(db.query(Inkassaciya).order_by(Inkassaciya.created_at.desc()), page, size)


@router.get("/{ink_id}")
def get_inkassaciya(ink_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.INKASSACIYA, Action.VIEW)
    ink = db.query(Inkassaciya).filter(Inkassaciya.id == ink_id).first()
    if ink is None:
        raise not_found("Инкассация не найдена")
    return serialize(ink)


@router.post("/start", status_code=201)
def start(data: InkStartIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    cash = db.query(CashRegister).filter(CashRegister.id == data.cash_id).first()
    if cash is None:
        raise not_found("Касса не найдена")
    principal.require(Resource.INKASSACIYA, Action.CREATE, business_id=cash.business_id, record_owner_id=cash.responsible_user_id)
    ink = ink_service.start(db, actor_id=principal.id, cash_id=data.cash_id, shift_ref=data.shift_ref)
    return serialize(ink)


@router.post("/{ink_id}/fact")
def submit_fact(ink_id: str, data: InkFactIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    ink = db.query(Inkassaciya).filter(Inkassaciya.id == ink_id).first()
    if ink is None:
        raise not_found("Инкассация не найдена")
    principal.require(Resource.INKASSACIYA, Action.CREATE, business_id=ink.business_id)
    result = ink_service.submit_fact(db, actor_id=principal.id, ink_id=ink_id, fact_amount=data.fact_amount)
    invalidate_summary()
    return serialize(result)


@router.post("/{ink_id}/accept")
def accept(ink_id: str, data: InkAcceptIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    ink = db.query(Inkassaciya).filter(Inkassaciya.id == ink_id).first()
    if ink is None:
        raise not_found("Инкассация не найдена")
    # Подтверждает получатель (директор/ответственный) — право confirm (§9.6.1)
    principal.require(Resource.INKASSACIYA, Action.CONFIRM)
    result = ink_service.accept(db, actor_id=principal.id, ink_id=ink_id, accepted_amount=data.accepted_amount)
    return serialize(result)
