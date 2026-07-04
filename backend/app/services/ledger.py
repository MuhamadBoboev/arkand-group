"""Append-only денежный ledger (§7.1, §9.6).

Проведённую проводку нельзя изменить/удалить — только сторно (reverse).
Баланс кассы вычисляется из движений, не хранится.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import MoneyKind, MoneyStatus
from app.core.errors import bad_request, conflict, not_found
from app.db.base import now_utc
from app.db.models import CashRegister, MoneyMovement, PeriodClose
from app.realtime import channels
from app.realtime.publisher import publish
from app.services.audit import write_audit


def _period_of(dt) -> str:
    return dt.strftime("%Y-%m")


def assert_period_open(db: Session, business_id: str, when=None) -> None:
    """Задним числом в закрытый период писать нельзя (§9.6)."""
    period = _period_of(when or now_utc())
    closed = (
        db.query(PeriodClose)
        .filter(PeriodClose.business_id == business_id, PeriodClose.period == period)
        .first()
    )
    if closed:
        raise conflict("period_closed", f"Период {period} закрыт — изменения только сторно в новом периоде")


def compute_cash_balance(db: Session, cash_id: str) -> Decimal:
    """Баланс = Σ(доход) − Σ(расход) по всем движениям кассы (сторно учтено как обратное движение)."""
    income = (
        db.query(func.coalesce(func.sum(MoneyMovement.amount), 0))
        .filter(MoneyMovement.cash_id == cash_id, MoneyMovement.kind == MoneyKind.INCOME)
        .scalar()
        or 0
    )
    expense = (
        db.query(func.coalesce(func.sum(MoneyMovement.amount), 0))
        .filter(MoneyMovement.cash_id == cash_id, MoneyMovement.kind == MoneyKind.EXPENSE)
        .scalar()
        or 0
    )
    return Decimal(income) - Decimal(expense)


def create_movement(
    db: Session,
    *,
    actor_id: str,
    cash_id: str,
    kind: str,
    amount: Decimal,
    article: str | None = None,
    basis_ref: str | None = None,
    counterparty_id: str | None = None,
    income_stage: str | None = None,
    status: str = MoneyStatus.IN_CASH,
    note: str | None = None,
    confirmed_by: str | None = None,
) -> MoneyMovement:
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if cash is None:
        raise not_found("Касса не найдена")
    if amount is None or Decimal(amount) <= 0:
        raise bad_request("bad_amount", "Сумма должна быть положительной")
    if kind not in (MoneyKind.INCOME, MoneyKind.EXPENSE):
        raise bad_request("bad_kind", "kind: income | expense")

    assert_period_open(db, cash.business_id)

    mv = MoneyMovement(
        cash_id=cash_id,
        business_id=cash.business_id,
        kind=kind,
        status=status,
        income_stage=income_stage,
        amount=Decimal(amount),
        article=article,
        basis_ref=basis_ref,
        counterparty_id=counterparty_id,
        note=note,
        confirmed_by=confirmed_by,
        confirmed_at=now_utc() if confirmed_by else None,
        created_by=actor_id,
    )
    db.add(mv)
    db.flush()
    write_audit(db, user_id=actor_id, action="create", resource="cash", ref_id=mv.id, after={
        "cash_id": cash_id, "kind": kind, "amount": str(amount), "status": status,
    })
    db.commit()
    db.refresh(mv)

    payload = {"id": mv.id, "cash_id": cash_id, "kind": kind, "amount": str(mv.amount), "status": status}
    publish(channels.cash(cash_id), "money_movement.created", payload)
    publish(channels.FINANCE, "money_movement.created", payload)
    return mv


def reverse_movement(db: Session, *, actor_id: str, movement_id: str, reason: str) -> MoneyMovement:
    """Сторно проводки — обратное видимое движение (§7.1). Оригинал не редактируется/не удаляется."""
    orig = db.query(MoneyMovement).filter(MoneyMovement.id == movement_id).first()
    if orig is None:
        raise not_found("Проводка не найдена")
    if orig.reversed:
        raise conflict("already_reversed", "Проводка уже сторнирована")
    if orig.is_reversal:
        raise conflict("is_reversal", "Нельзя сторнировать сторно-операцию")

    assert_period_open(db, orig.business_id)

    opposite = MoneyKind.EXPENSE if orig.kind == MoneyKind.INCOME else MoneyKind.INCOME
    rev = MoneyMovement(
        cash_id=orig.cash_id,
        business_id=orig.business_id,
        kind=opposite,
        status=orig.status,
        amount=orig.amount,
        article=f"СТОРНО: {orig.article or ''}".strip(),
        basis_ref=orig.id,
        note=reason,
        is_reversal=True,
        reversal_of=orig.id,
        created_by=actor_id,
    )
    orig.reversed = True  # маркер, не изменение суммы/типа
    db.add(rev)
    db.flush()
    write_audit(
        db, user_id=actor_id, action="reverse", resource="cash", ref_id=orig.id,
        before={"reversed": False}, after={"reversed": True, "reversal_id": rev.id, "reason": reason},
    )
    db.commit()
    db.refresh(rev)

    payload = {"id": rev.id, "cash_id": orig.cash_id, "reversal_of": orig.id, "amount": str(rev.amount)}
    publish(channels.cash(orig.cash_id), "money_movement.reversed", payload)
    publish(channels.FINANCE, "money_movement.reversed", payload)
    return rev
