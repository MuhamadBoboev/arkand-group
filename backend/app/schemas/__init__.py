"""Pydantic-схемы (v2). Валидация всего ввода на бэке (§14)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ---------- Auth ----------
class LoginIn(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PermissionOut(BaseModel):
    resource: str
    action: str
    scope: str


class MeOut(BaseModel):
    id: str
    full_name: str
    phone: str
    is_owner: bool
    owner_type: str | None
    roles: list[str]
    permissions: list[PermissionOut]
    businesses: list[str]


# ---------- Справочники ----------
class CounterpartyIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str | None = None
    inn: str | None = None
    phone: str | None = None
    note: str | None = None


class NomenclatureIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit_id: str | None = None
    category: str | None = None


class UnitIn(BaseModel):
    code: str
    title: str | None = None


# ---------- Финансы ----------
class CashIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    business_id: str
    limit_amount: Decimal | None = None
    responsible_user_id: str | None = None


class MovementIn(BaseModel):
    cash_id: str
    kind: str = Field(pattern="^(income|expense)$")
    amount: Decimal = Field(gt=0)
    article: str | None = None
    basis_ref: str | None = None
    counterparty_id: str | None = None
    income_stage: str | None = Field(default=None, pattern="^(advance|worked|revenue)$")
    note: str | None = None
    approval_ref: str | None = None  # id одобренного согласования для крупного расхода (§8.2)


class ReverseIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# ---------- Инкассация (§9.6.1) ----------
class InkStartIn(BaseModel):
    cash_id: str
    shift_ref: str | None = None


class InkFactIn(BaseModel):
    fact_amount: Decimal = Field(ge=0)


class InkAcceptIn(BaseModel):
    accepted_amount: Decimal = Field(ge=0)


# ---------- Снабжение ----------
class SupplyRequestIn(BaseModel):
    business_id: str
    items: list[dict[str, Any]]
    note: str | None = None


class PurchaseIn(BaseModel):
    business_id: str
    amount: Decimal = Field(gt=0)
    request_id: str | None = None
    supplier_id: str | None = None


class ReceiveIn(BaseModel):
    business_id: str
    nomenclature_id: str
    qty: Decimal = Field(gt=0)
    purchase_id: str | None = None
    shortage: Decimal | None = None
    surplus: Decimal | None = None
    source_business: str | None = None
    transfer_amount: Decimal | None = None  # денежная оценка межбизнес-передачи (§9.5)


class VoteIn(BaseModel):
    decision: str = Field(pattern="^(yes|no)$")


class ApprovalCreateIn(BaseModel):
    kind: str
    ref_id: str | None = None
    amount: Decimal | None = None
    note: str | None = None


# ---------- Владельцы / HR / задачи / календарь ----------
class EmployeeIn(BaseModel):
    user_id: str
    business_id: str | None = None
    position: str | None = None
    salary: Decimal | None = None


class AccessIn(BaseModel):
    user_id: str
    resource: str
    action: str
    scope: str = "all"
    business_id: str | None = None
    active: bool = True


class TaskIn(BaseModel):
    assigned_to: str
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    business_scope: str | None = None
    due_at: str | None = None


class TaskStatusIn(BaseModel):
    status: str = Field(pattern="^(open|in_progress|done|cancelled)$")


class CalendarIn(BaseModel):
    type: str | None = None
    title: str = Field(min_length=1, max_length=300)
    at: str | None = None
    participants: list[str] | None = None
    owner_scope: str | None = None


class PeriodCloseIn(BaseModel):
    business_id: str
    period: str = Field(pattern=r"^\d{4}-\d{2}$")


# ---------- Отдел проверки (§9.8) ----------
class ActIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    business_id: str | None = None
    plan_id: str | None = None
    summary: str | None = None


class RemarkIn(BaseModel):
    act_id: str
    text: str = Field(min_length=1)


class EscalationIn(BaseModel):
    act_id: str | None = None
    remark_id: str | None = None
    reason: str = Field(min_length=1)
    bypass_business: str | None = None


# ---------- Общие ----------
class GenericCreate(BaseModel):
    """Гибкое создание сущности модуля бизнеса — поля валидируются на уровне сервиса."""
    model_config = {"extra": "allow"}
