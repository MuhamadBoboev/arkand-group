"""Снабжение (§9.5, §11)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize, serialize_list
from app.core.constants import Action, Resource
from app.core.deps import get_principal
from app.core.errors import forbidden, not_found
from app.db.base import get_db
from app.db.models import Limit, Purchase, Quote, Supplier, SupplyRequest
from app.schemas import PurchaseIn, ReceiveIn, SupplyRequestIn
from app.services import supply as supply_service
from app.services.audit import write_audit
from app.services.rbac import Principal

router = APIRouter(prefix="/supply", tags=["supply"])


@router.get("/requests")
def list_requests(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.SUPPLY_REQUEST, Action.VIEW)
    return paginate(db.query(SupplyRequest).order_by(SupplyRequest.created_at.desc()), page, size)


@router.post("/requests", status_code=201)
def create_request(data: SupplyRequestIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.SUPPLY_REQUEST, Action.CREATE, business_id=data.business_id)
    req = supply_service.create_request(db, actor_id=principal.id, business_id=data.business_id, items=data.items, note=data.note)
    return serialize(req)


@router.get("/purchases")
def list_purchases(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PURCHASE, Action.VIEW)
    return paginate(db.query(Purchase).order_by(Purchase.created_at.desc()), page, size)


@router.post("/purchases", status_code=201)
def create_purchase(data: PurchaseIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PURCHASE, Action.CREATE, business_id=data.business_id)
    pur, approval = supply_service.create_purchase(
        db, actor_id=principal.id, business_id=data.business_id, amount=data.amount,
        request_id=data.request_id, supplier_id=data.supplier_id,
    )
    out = serialize(pur)
    out["approval"] = serialize(approval) if approval else None
    return out


@router.post("/receive", status_code=201)
def receive(data: ReceiveIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.WAREHOUSE, Action.CREATE, business_id=data.business_id)
    rec = supply_service.receive(
        db, actor_id=principal.id, business_id=data.business_id, nomenclature_id=data.nomenclature_id,
        qty=data.qty, purchase_id=data.purchase_id, shortage=data.shortage, surplus=data.surplus,
        source_business=data.source_business, transfer_amount=data.transfer_amount,
    )
    return serialize(rec)


# ---------- Поставщики / КП ----------
@router.get("/suppliers")
def list_suppliers(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PURCHASE, Action.VIEW)
    return serialize_list(db.query(Supplier).order_by(Supplier.created_at.desc()).all())


@router.post("/suppliers", status_code=201)
def create_supplier(counterparty_id: str = Query(...), rating: int | None = None, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PURCHASE, Action.CREATE)
    s = Supplier(counterparty_id=counterparty_id, rating=rating, created_by=principal.id)
    db.add(s)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="purchase", ref_id=s.id, after={"counterparty_id": counterparty_id})
    db.commit()
    db.refresh(s)
    return serialize(s)


@router.get("/quotes")
def list_quotes(request_id: str | None = Query(default=None), principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PURCHASE, Action.VIEW)
    q = db.query(Quote)
    if request_id:
        q = q.filter(Quote.request_id == request_id)
    return serialize_list(q.order_by(Quote.amount).all())


@router.post("/quotes", status_code=201)
def create_quote(request_id: str = Query(...), supplier_id: str = Query(...), amount: Decimal = Query(gt=0), principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PURCHASE, Action.CREATE)
    qt = Quote(request_id=request_id, supplier_id=supplier_id, amount=Decimal(amount), created_by=principal.id)
    db.add(qt)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="purchase", ref_id=qt.id, after={"amount": str(amount)})
    db.commit()
    db.refresh(qt)
    return serialize(qt)


# ---------- Лимиты (меняют только владельцы §8.4) ----------
@router.get("/limits")
def list_limits(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    return serialize_list(db.query(Limit).order_by(Limit.created_at.desc()).all())


@router.post("/limits", status_code=201)
def create_limit(business_id: str | None = None, amount: Decimal = Query(gt=0), resource: str | None = None, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    if not principal.is_owner:
        raise forbidden("Лимиты меняют только владельцы (§8.4)")
    lim = Limit(business_id=business_id, amount=Decimal(amount), resource=resource, set_by=principal.id, created_by=principal.id)
    db.add(lim)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="purchase", ref_id=lim.id, after={"amount": str(amount), "business_id": business_id})
    db.commit()
    db.refresh(lim)
    return serialize(lim)
