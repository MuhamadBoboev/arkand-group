"""Снабжение (§9.5): заявки, закупки (лимит → согласование троих), оприходование→склад, долги."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DebtStatus
from app.core.errors import not_found
from app.db.models import Debt, Limit, Purchase, Receipt, SupplyRequest
from app.realtime import channels
from app.realtime.publisher import publish
from app.services import approvals, warehouse
from app.services.audit import write_audit


def create_request(db: Session, *, actor_id: str, business_id: str, items: list, note: str | None = None) -> SupplyRequest:
    req = SupplyRequest(business_id=business_id, items_json=items, status="new", note=note, created_by=actor_id)
    db.add(req)
    db.flush()
    write_audit(db, user_id=actor_id, action="create", resource="supply_request", ref_id=req.id,
                after={"business_id": business_id, "items": items})
    db.commit()
    db.refresh(req)
    publish(channels.SUPPLY, "supply_request.created", {"id": req.id, "business_id": business_id})
    publish(channels.business(business_id), "supply_request.created", {"id": req.id})
    return req


def limit_for(db: Session, business_id: str) -> Decimal:
    """Порог для бизнеса: явный Limit или общий порог крупного расхода (§8.2)."""
    row = (
        db.query(func.min(Limit.amount))
        .filter((Limit.business_id == business_id) | (Limit.business_id.is_(None)))
        .scalar()
    )
    return Decimal(row) if row is not None else settings.large_expense_threshold


def create_purchase(
    db: Session, *, actor_id: str, business_id: str, amount: Decimal,
    request_id: str | None = None, supplier_id: str | None = None,
) -> tuple[Purchase, object | None]:
    """В лимите — сам; крупно → согласование троих (§9.5, §8.2)."""
    threshold = limit_for(db, business_id)
    within = Decimal(amount) <= threshold

    pur = Purchase(
        request_id=request_id, supplier_id=supplier_id, business_id=business_id,
        amount=Decimal(amount), limit_ok=within,
        status="approved" if within else "pending_approval", created_by=actor_id,
    )
    db.add(pur)
    db.flush()

    approval = None
    if not within:
        approval = approvals.create_approval(
            db, kind="purchase", ref_id=pur.id, amount=Decimal(amount),
            note=f"Крупная закупка бизнеса {business_id}", actor_id=actor_id,
        )
        pur.approval_ref = approval.id

    write_audit(db, user_id=actor_id, action="create", resource="purchase", ref_id=pur.id,
                after={"amount": str(amount), "limit_ok": within, "status": pur.status})
    db.commit()
    db.refresh(pur)
    publish(channels.SUPPLY, "purchase.created", {"id": pur.id, "status": pur.status, "amount": str(amount)})
    return pur, approval


def receive(
    db: Session, *, actor_id: str, business_id: str, nomenclature_id: str, qty: Decimal,
    purchase_id: str | None = None, shortage: Decimal | None = None, surplus: Decimal | None = None,
    source_business: str | None = None, transfer_amount: Decimal | None = None,
) -> Receipt:
    """Оприходование на склад бизнеса → синхронизация склада (§6.3). Межбизнес-передача = долг (§9.5)."""
    rec = Receipt(
        purchase_id=purchase_id, business_id=business_id, nomenclature_id=nomenclature_id,
        qty=Decimal(qty), shortage=shortage, surplus=surplus, created_by=actor_id,
    )
    db.add(rec)
    db.flush()

    # склад получателя сразу видит новый остаток (§6.3)
    warehouse.adjust(
        db, actor_id=actor_id, business_id=business_id, nomenclature_id=nomenclature_id,
        delta_qty=Decimal(qty), kind="receipt", basis_ref=rec.id,
    )

    # межбизнес-передача → долг (денежная оценка) + списание со склада отправителя
    if source_business and source_business != business_id:
        warehouse.adjust(
            db, actor_id=actor_id, business_id=source_business, nomenclature_id=nomenclature_id,
            delta_qty=-Decimal(qty), kind="issue", basis_ref=rec.id,
        )
        amount = transfer_amount
        if amount is None and purchase_id:
            pur = db.query(Purchase).filter(Purchase.id == purchase_id).first()
            amount = Decimal(pur.amount) if pur else Decimal(qty)
        if amount is None:
            amount = Decimal(qty)
        debt = Debt(
            from_business=business_id, to_business=source_business,
            amount=Decimal(amount), status=DebtStatus.OPEN, basis_ref=rec.id, created_by=actor_id,
        )
        db.add(debt)
        db.flush()
        publish(channels.FINANCE, "debt.created", {"id": debt.id, "from": business_id, "to": source_business, "amount": str(amount)})

    write_audit(db, user_id=actor_id, action="create", resource="warehouse", ref_id=rec.id,
                after={"business_id": business_id, "nomenclature_id": nomenclature_id, "qty": str(qty)})
    db.commit()
    db.refresh(rec)
    publish(channels.SUPPLY, "receipt.created", {"id": rec.id, "business_id": business_id})
    return rec
