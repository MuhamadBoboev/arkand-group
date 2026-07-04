"""Финансы (§9.6): кассы, проводки (append-only), сторно, долги, зарплата, закрытие периода."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize, serialize_list
from app.core.constants import Action, ApprovalResult, DebtStatus, MoneyKind, Resource
from app.core.deps import get_principal
from app.core.errors import conflict, forbidden, not_found
from app.db.base import get_db
from app.db.models import Approval, CashRegister, Debt, MoneyMovement, PeriodClose, Salary
from app.schemas import CashIn, MovementIn, PeriodCloseIn, ReverseIn
from app.services import approvals as approvals_service
from app.services import ledger
from app.services import supply as supply_service
from app.services.analytics import invalidate_summary
from app.services.audit import write_audit
from app.services.rbac import Principal

router = APIRouter(prefix="/finance", tags=["finance"])


def _visible_cash(principal: Principal, db: Session) -> list[CashRegister]:
    out = []
    for c in db.query(CashRegister).all():
        if principal.can(Resource.CASH, Action.VIEW, business_id=c.business_id, record_owner_id=c.responsible_user_id):
            out.append(c)
    return out


@router.get("/cash")
def list_cash(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = []
    for c in _visible_cash(principal, db):
        d = serialize(c)
        d["balance"] = str(ledger.compute_cash_balance(db, c.id))
        rows.append(d)
    return {"items": rows, "total": len(rows)}


@router.post("/cash", status_code=201)
def create_cash(data: CashIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.CASH, Action.CREATE, business_id=data.business_id)
    c = CashRegister(**data.model_dump(), created_by=principal.id)
    db.add(c)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="cash", ref_id=c.id, after=data.model_dump())
    db.commit()
    db.refresh(c)
    return serialize(c)


@router.get("/cash/{cash_id}/balance")
def cash_balance(cash_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    c = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if c is None:
        raise not_found("Касса не найдена")
    principal.require(Resource.CASH, Action.VIEW, business_id=c.business_id, record_owner_id=c.responsible_user_id)
    return {"cash_id": cash_id, "balance": str(ledger.compute_cash_balance(db, cash_id))}


@router.get("/movements")
def list_movements(
    cash_id: str | None = Query(default=None),
    page: int = 1,
    size: int = 50,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    query = db.query(MoneyMovement)
    if cash_id:
        c = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
        if c is None:
            raise not_found("Касса не найдена")
        principal.require(Resource.CASH, Action.VIEW, business_id=c.business_id, record_owner_id=c.responsible_user_id)
        query = query.filter(MoneyMovement.cash_id == cash_id)
    else:
        # без указания кассы — только для тех, кто видит финансы целиком
        principal.require(Resource.CASH, Action.VIEW)
        visible_ids = [c.id for c in _visible_cash(principal, db)]
        query = query.filter(MoneyMovement.cash_id.in_(visible_ids or ["-"]))
    return paginate(query.order_by(MoneyMovement.created_at.desc()), page, size)


@router.post("/movements", status_code=201)
def create_movement(data: MovementIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    c = db.query(CashRegister).filter(CashRegister.id == data.cash_id).first()
    if c is None:
        raise not_found("Касса не найдена")
    # Кассир — только своя касса (scope own_records §8.4)
    principal.require(Resource.CASH, Action.CREATE, business_id=c.business_id, record_owner_id=c.responsible_user_id)

    # Крупный расход → согласование всех троих (§8.2)
    if data.kind == MoneyKind.EXPENSE:
        threshold = supply_service.limit_for(db, c.business_id)
        if Decimal(data.amount) > threshold:
            if not data.approval_ref:
                ap = approvals_service.create_approval(
                    db, kind="expense", ref_id=None, amount=Decimal(data.amount),
                    note=f"Крупный расход по кассе {c.name}", actor_id=principal.id,
                )
                db.commit()
                raise conflict("approval_required", "Крупный расход требует согласования троих владельцев",
                               {"approval_id": ap.id, "threshold": str(threshold)})
            ap = db.query(Approval).filter(Approval.id == data.approval_ref).first()
            if ap is None or ap.result != ApprovalResult.APPROVED or ap.kind != "expense":
                raise forbidden("Расход не согласован владельцами")

    mv = ledger.create_movement(
        db, actor_id=principal.id, cash_id=data.cash_id, kind=data.kind, amount=data.amount,
        article=data.article, basis_ref=data.basis_ref, counterparty_id=data.counterparty_id,
        income_stage=data.income_stage, note=data.note,
        confirmed_by=principal.id if principal.can(Resource.CASH, Action.CONFIRM) else None,
    )
    invalidate_summary()
    return serialize(mv)


@router.post("/movements/{movement_id}/reverse", status_code=201)
def reverse_movement(movement_id: str, data: ReverseIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    mv = db.query(MoneyMovement).filter(MoneyMovement.id == movement_id).first()
    if mv is None:
        raise not_found("Проводка не найдена")
    principal.require(Resource.CASH, Action.UPDATE_VIA_REVERSAL, business_id=mv.business_id)
    rev = ledger.reverse_movement(db, actor_id=principal.id, movement_id=movement_id, reason=data.reason)
    invalidate_summary()
    return serialize(rev)


# ---------- Долги ----------
@router.get("/debts")
def list_debts(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.DEBT, Action.VIEW)
    return paginate(db.query(Debt).order_by(Debt.created_at.desc()), page, size)


@router.post("/debts/{debt_id}/pay", status_code=200)
def pay_debt(debt_id: str, amount: Decimal = Query(gt=0), principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.DEBT, Action.CREATE)
    debt = db.query(Debt).filter(Debt.id == debt_id).first()
    if debt is None:
        raise not_found("Долг не найден")
    debt.paid_amount = Decimal(debt.paid_amount) + Decimal(amount)
    if Decimal(debt.paid_amount) >= Decimal(debt.amount):
        debt.status = DebtStatus.CLOSED
    elif Decimal(debt.paid_amount) > 0:
        debt.status = DebtStatus.PARTIAL
    write_audit(db, user_id=principal.id, action="update_via_reversal", resource="debt", ref_id=debt.id,
                after={"paid_amount": str(debt.paid_amount), "status": debt.status})
    db.commit()
    db.refresh(debt)
    return serialize(debt)


# ---------- Зарплата ----------
@router.get("/salaries")
def list_salaries(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.SALARY, Action.VIEW)
    return paginate(db.query(Salary).order_by(Salary.created_at.desc()), page, size)


@router.post("/salaries/{salary_id}/pay")
def confirm_salary(salary_id: str, amount: Decimal = Query(gt=0), principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    # Факт выплаты подтверждается в системе (§13 — вручную)
    principal.require(Resource.SALARY, Action.CONFIRM)
    sal = db.query(Salary).filter(Salary.id == salary_id).first()
    if sal is None:
        raise not_found("Начисление не найдено")
    from app.db.base import now_utc

    sal.paid = Decimal(sal.paid) + Decimal(amount)
    sal.paid_confirmed_at = now_utc()
    write_audit(db, user_id=principal.id, action="confirm", resource="salary", ref_id=sal.id,
                after={"paid": str(sal.paid)})
    db.commit()
    db.refresh(sal)
    return serialize(sal)


# ---------- Закрытие периода ----------
@router.get("/period")
def list_periods(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PERIOD, Action.VIEW)
    return serialize_list(db.query(PeriodClose).order_by(PeriodClose.created_at.desc()).all())


@router.post("/period/close", status_code=201)
def close_period(data: PeriodCloseIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.PERIOD, Action.CREATE, business_id=data.business_id)
    exists = db.query(PeriodClose).filter(
        PeriodClose.business_id == data.business_id, PeriodClose.period == data.period
    ).first()
    if exists:
        raise forbidden("Период уже закрыт")
    pc = PeriodClose(business_id=data.business_id, period=data.period, closed_by=principal.id, created_by=principal.id)
    db.add(pc)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="period", ref_id=pc.id, after=data.model_dump())
    db.commit()
    db.refresh(pc)
    return serialize(pc)
