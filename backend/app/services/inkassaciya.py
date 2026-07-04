"""Инкассация (§9.6.1) — реализовано точно по шагам ТЗ.

Состояния: в_кассе → в_пути → принято, плюс расхождение.
Остаток только вычисляется; инкассация двусторонняя (передал ≠ подтвердил);
задним числом не редактируется — только сторно.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import InkassaciyaStatus, MoneyKind, MoneyStatus
from app.core.errors import bad_request, conflict, not_found
from app.db.base import now_utc
from app.db.models import CashRegister, Inkassaciya
from app.realtime import channels
from app.realtime.publisher import publish
from app.services import ledger
from app.services.audit import write_audit


def _publish(ink: Inkassaciya, type_: str) -> None:
    payload = {
        "id": ink.id, "cash_id": ink.cash_id, "status": ink.status,
        "calc_amount": str(ink.calc_amount),
        "fact_amount": str(ink.fact_amount) if ink.fact_amount is not None else None,
        "discrepancy": str(ink.discrepancy) if ink.discrepancy is not None else None,
    }
    publish(channels.cash(ink.cash_id), type_, payload)
    publish(channels.FINANCE, type_, payload)


def start(db: Session, *, actor_id: str, cash_id: str, shift_ref: str | None = None) -> Inkassaciya:
    """Шаг 1: система показывает расчётный остаток (справочно)."""
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if cash is None:
        raise not_found("Касса не найдена")

    calc = ledger.compute_cash_balance(db, cash_id)  # нал-продажи − расходы + приходы
    ink = Inkassaciya(
        cash_id=cash_id,
        business_id=cash.business_id,
        calc_amount=calc,
        status=InkassaciyaStatus.IN_CASH,
        sent_by=actor_id,
        shift_ref=shift_ref,
        created_by=actor_id,
    )
    db.add(ink)
    db.flush()
    write_audit(db, user_id=actor_id, action="create", resource="inkassaciya", ref_id=ink.id,
                after={"cash_id": cash_id, "calc_amount": str(calc)})
    db.commit()
    db.refresh(ink)
    _publish(ink, "inkassaciya.started")
    return ink


def submit_fact(db: Session, *, actor_id: str, ink_id: str, fact_amount: Decimal) -> Inkassaciya:
    """Шаги 2-4: кассир вводит факт → видимая операция расхождения → деньги в_пути."""
    ink = db.query(Inkassaciya).filter(Inkassaciya.id == ink_id).first()
    if ink is None:
        raise not_found("Инкассация не найдена")
    if ink.status != InkassaciyaStatus.IN_CASH:
        raise conflict("bad_state", "Факт можно ввести только в статусе «в кассе»")
    if fact_amount is None or Decimal(fact_amount) < 0:
        raise bad_request("bad_amount", "Фактическая сумма обязательна и не может быть отрицательной")

    ledger.assert_period_open(db, ink.business_id)
    fact = Decimal(fact_amount)
    discrepancy = fact - Decimal(ink.calc_amount)  # + излишек / − недостача

    # Шаг 3: расхождение → отдельная ВИДИМАЯ операция недостача/излишек (привязка к смене+кассиру)
    if discrepancy != 0:
        is_surplus = discrepancy > 0
        ledger.create_movement(
            db,
            actor_id=actor_id,
            cash_id=ink.cash_id,
            kind=MoneyKind.INCOME if is_surplus else MoneyKind.EXPENSE,
            amount=abs(discrepancy),
            article="Излишек при инкассации" if is_surplus else "Недостача при инкассации",
            basis_ref=ink.id,
            note=f"Инкассация {ink.id}, смена {ink.shift_ref or '-'}",
        )

    # Физически пересчитанная сумма уходит из кассы в путь
    if fact > 0:
        ledger.create_movement(
            db,
            actor_id=actor_id,
            cash_id=ink.cash_id,
            kind=MoneyKind.EXPENSE,
            amount=fact,
            article="Инкассация — передано в путь",
            basis_ref=ink.id,
            status=MoneyStatus.IN_TRANSIT,
        )

    ink.fact_amount = fact
    ink.discrepancy = discrepancy
    ink.status = InkassaciyaStatus.IN_TRANSIT  # Шаг 4: деньги → в_пути
    db.add(ink)
    db.flush()
    write_audit(db, user_id=actor_id, action="update_via_reversal", resource="inkassaciya", ref_id=ink.id,
                after={"fact_amount": str(fact), "discrepancy": str(discrepancy), "status": ink.status})
    db.commit()
    db.refresh(ink)
    _publish(ink, "inkassaciya.in_transit")
    return ink


def accept(db: Session, *, actor_id: str, ink_id: str, accepted_amount: Decimal) -> Inkassaciya:
    """Шаги 5-6: получатель (другой логин) подтверждает принятую сумму."""
    ink = db.query(Inkassaciya).filter(Inkassaciya.id == ink_id).first()
    if ink is None:
        raise not_found("Инкассация не найдена")
    if ink.status != InkassaciyaStatus.IN_TRANSIT:
        raise conflict("bad_state", "Подтвердить можно только сумму в пути")

    # Двусторонность: передал ≠ подтвердил (§7.6, §9.6.1)
    if actor_id == ink.sent_by:
        raise conflict("same_user", "Подтвердить инкассацию должен другой пользователь (не кассир)")

    accepted = Decimal(accepted_amount)
    ink.accepted_by = actor_id
    ink.accepted_amount = accepted
    ink.accepted_at = now_utc()

    if accepted == Decimal(ink.fact_amount):
        ink.status = InkassaciyaStatus.ACCEPTED           # Шаг 6: совпало → принято
    else:
        ink.status = InkassaciyaStatus.DISCREPANCY        # расхождение «по дороге», видно обоим и отделу проверки

    db.add(ink)
    db.flush()
    write_audit(db, user_id=actor_id, action="confirm", resource="inkassaciya", ref_id=ink.id,
                after={"accepted_by": actor_id, "accepted_amount": str(accepted), "status": ink.status})
    db.commit()
    db.refresh(ink)
    _publish(ink, "inkassaciya.accepted" if ink.status == InkassaciyaStatus.ACCEPTED else "inkassaciya.discrepancy")
    return ink
