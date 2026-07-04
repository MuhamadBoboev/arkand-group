"""Модель данных PostgreSQL (§10) + сущности модулей (§9).

Принципы (§10):
- денежные/складские таблицы append-only (корректировка = строка-сторно, не UPDATE/DELETE);
- суммы — Numeric(18,2), никогда float;
- все значимые таблицы: id(uuid), created_at, created_by, business_id (где применимо).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base, Timestamped, UUIDPk, new_id, now_utc

MONEY = Numeric(18, 2)


# ======================================================================
#  AUTH / RBAC (§8, §10)
# ======================================================================
class User(Base, UUIDPk, Timestamped):
    __tablename__ = "users"
    full_name = Column(String(200), nullable=False)
    phone = Column(String(32), unique=True, nullable=False, index=True)  # логин
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Role(Base, UUIDPk, Timestamped):
    __tablename__ = "roles"
    name = Column(String(100), unique=True, nullable=False)
    title = Column(String(200), nullable=True)


class Permission(Base, UUIDPk, Timestamped):
    __tablename__ = "permissions"
    resource = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    scope = Column(String(64), nullable=False, default="all")
    __table_args__ = (UniqueConstraint("resource", "action", "scope", name="uq_permission"),)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(String(36), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String(36), ForeignKey("permissions.id"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id"), primary_key=True)


class Owner(Base, UUIDPk, Timestamped):
    """Владельцы + правила защиты (§8.2)."""
    __tablename__ = "owners"
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    owner_type = Column(String(32), nullable=False)  # sohib / iftikhor / dovud


class AccessGrant(Base, UUIDPk, Timestamped):
    """Выданный/отключённый доступ по человеку (§8.3, §10)."""
    __tablename__ = "access_grants"
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(String(36), ForeignKey("permissions.id"), nullable=False)
    business_id = Column(String(36), nullable=True)  # ограничение области, если нужно
    granted_by = Column(String(36), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    disabled_by = Column(String(36), nullable=True)
    disabled_at = Column(DateTime(timezone=True), nullable=True)


class Employee(Base, UUIDPk, Timestamped):
    """Сотрудник: оклад, приём/увольнение (§8.3, §9.7)."""
    __tablename__ = "employees"
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), nullable=True, index=True)
    position = Column(String(200), nullable=True)
    salary = Column(MONEY, nullable=True)
    hired_at = Column(Date, nullable=True)
    fired_at = Column(Date, nullable=True)


# ======================================================================
#  ЕДИНЫЕ СПРАВОЧНИКИ (§7.5, §10)
# ======================================================================
class BusinessEntity(Base, UUIDPk, Timestamped):
    __tablename__ = "businesses"
    name = Column(String(200), nullable=False)
    type = Column(String(32), nullable=False)  # zastroyshchik / proektnaya / beton / shcheben / supply / ...


class Counterparty(Base, UUIDPk, Timestamped):
    """ЕДИНЫЙ реестр контрагентов: один контрагент = одна карточка на все бизнесы (§7.5)."""
    __tablename__ = "counterparties"
    name = Column(String(200), nullable=False, unique=True)
    type = Column(String(64), nullable=True)  # поставщик / клиент / подрядчик
    inn = Column(String(64), nullable=True)
    phone = Column(String(64), nullable=True)
    note = Column(Text, nullable=True)


class Unit(Base, UUIDPk, Timestamped):
    __tablename__ = "units"
    code = Column(String(32), unique=True, nullable=False)  # шт, м3, кг, т, ...
    title = Column(String(64), nullable=True)


class Nomenclature(Base, UUIDPk, Timestamped):
    """Единая номенклатура. Свободный текст запрещён — только отсюда (§7.5)."""
    __tablename__ = "nomenclature"
    name = Column(String(200), nullable=False, unique=True)
    unit_id = Column(String(36), ForeignKey("units.id"), nullable=True)
    category = Column(String(100), nullable=True)


# ======================================================================
#  ФИНАНСЫ — append-only ledger (§9.6, §10)
# ======================================================================
class CashRegister(Base, UUIDPk, Timestamped):
    __tablename__ = "cash_registers"
    name = Column(String(200), nullable=False)
    business_id = Column(String(36), nullable=False, index=True)
    limit_amount = Column(MONEY, nullable=True)  # лимит кассы (меняют владельцы)
    responsible_user_id = Column(String(36), nullable=True)  # кассир своей кассы (§8.4)


class MoneyMovement(Base, UUIDPk, Timestamped):
    """Append-only проводка. Корректировка — только сторно (is_reversal), не UPDATE/DELETE (§7.1)."""
    __tablename__ = "money_movements"
    cash_id = Column(String(36), ForeignKey("cash_registers.id"), nullable=False, index=True)
    business_id = Column(String(36), nullable=False, index=True)
    kind = Column(String(16), nullable=False)          # income / expense
    status = Column(String(16), nullable=False, default="in_cash")  # in_cash/in_transit/accepted/discrepancy
    income_stage = Column(String(16), nullable=True)   # advance/worked/revenue (аванс ≠ выручка §7.4)
    amount = Column(MONEY, nullable=False)
    article = Column(String(200), nullable=True)       # статья
    basis_ref = Column(String(200), nullable=True)     # привязка к основанию (§9.6 правила)
    counterparty_id = Column(String(36), nullable=True)
    note = Column(Text, nullable=True)
    confirmed_by = Column(String(36), nullable=True)    # подтверждение финансистом
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    is_reversal = Column(Boolean, default=False, nullable=False)
    reversal_of = Column(String(36), ForeignKey("money_movements.id"), nullable=True)
    reversed = Column(Boolean, default=False, nullable=False)  # помечена как сторнированная


class Inkassaciya(Base, UUIDPk, Timestamped):
    """Инкассация (§9.6.1) — двусторонняя, со статусами и фиксацией расхождений."""
    __tablename__ = "inkassaciya"
    cash_id = Column(String(36), ForeignKey("cash_registers.id"), nullable=False, index=True)
    business_id = Column(String(36), nullable=False, index=True)
    calc_amount = Column(MONEY, nullable=False)        # расчётный остаток (только вычисляется)
    fact_amount = Column(MONEY, nullable=True)          # фактически пересчитанная сумма
    discrepancy = Column(MONEY, nullable=True)          # недостача(−)/излишек(+)
    status = Column(String(16), nullable=False, default="in_cash")
    sent_by = Column(String(36), nullable=True)         # кассир (передал)
    accepted_by = Column(String(36), nullable=True)     # получатель (подтвердил) — другой логин
    accepted_amount = Column(MONEY, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    shift_ref = Column(String(200), nullable=True)      # привязка к смене


class Debt(Base, UUIDPk, Timestamped):
    """Долги, в т.ч. межбизнес-передача = долг (§9.5)."""
    __tablename__ = "debts"
    from_business = Column(String(36), nullable=False, index=True)
    to_business = Column(String(36), nullable=False, index=True)
    counterparty_id = Column(String(36), nullable=True)
    amount = Column(MONEY, nullable=False)
    paid_amount = Column(MONEY, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="open")
    basis_ref = Column(String(200), nullable=True)


class Salary(Base, UUIDPk, Timestamped):
    __tablename__ = "salaries"
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False)          # YYYY-MM
    accrued = Column(MONEY, nullable=False, default=0)
    paid = Column(MONEY, nullable=False, default=0)
    paid_confirmed_at = Column(DateTime(timezone=True), nullable=True)  # ручное подтверждение (§13)


class Timesheet(Base, UUIDPk, Timestamped):
    __tablename__ = "timesheets"
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False)
    days = Column(Numeric(6, 2), nullable=True)
    note = Column(Text, nullable=True)


class BarterOperation(Base, UUIDPk, Timestamped):
    """Бартер по утверждённому владельцами прайсу (§9.3/§9.4)."""
    __tablename__ = "barter_operations"
    from_business = Column(String(36), nullable=False)
    to_business = Column(String(36), nullable=False)
    nomenclature_id = Column(String(36), nullable=True)
    qty = Column(Numeric(18, 3), nullable=True)
    price_frozen = Column(MONEY, nullable=True)  # заморожен прайс на дату
    amount = Column(MONEY, nullable=False)
    approved_by = Column(String(36), nullable=True)


class PeriodClose(Base, UUIDPk, Timestamped):
    """Закрытие периода — после него задним числом не изменить (§9.6)."""
    __tablename__ = "period_close"
    business_id = Column(String(36), nullable=False, index=True)
    period = Column(String(7), nullable=False)
    closed_by = Column(String(36), nullable=False)
    __table_args__ = (UniqueConstraint("business_id", "period", name="uq_period_close"),)


# ======================================================================
#  ПРОИЗВОДСТВО / СКЛАД (§9.1-9.4, §10)
# ======================================================================
class Order(Base, UUIDPk, Timestamped):
    """Заказ; рецептура/цена замораживается копией (§7.3)."""
    __tablename__ = "orders"
    business_id = Column(String(36), nullable=False, index=True)
    counterparty_id = Column(String(36), nullable=True)
    title = Column(String(200), nullable=True)
    mark = Column(String(64), nullable=True)            # марка (бетон) / фракция (щебень)
    volume = Column(Numeric(18, 3), nullable=True)
    amount = Column(MONEY, nullable=True)
    payment_status = Column(String(32), nullable=True)  # аванс/оплачено/долг
    status = Column(String(16), nullable=False, default="new")  # + cancelled/returned/partial/defect
    payload_frozen = Column(JSON, nullable=True)        # замороженная копия параметров
    is_reversal = Column(Boolean, default=False, nullable=False)
    reversal_of = Column(String(36), ForeignKey("orders.id"), nullable=True)
    reversed = Column(Boolean, default=False, nullable=False)


class Recipe(Base, UUIDPk, Timestamped):
    """Рецептура 1м³; замороженная копия уходит в заказ (§7.3)."""
    __tablename__ = "recipes"
    business_id = Column(String(36), nullable=False, index=True)
    mark = Column(String(64), nullable=False)
    frozen_json = Column(JSON, nullable=False)   # состав на 1 ед.
    valid_from = Column(Date, default=date.today, nullable=False)


class WarehouseStock(Base, UUIDPk, Timestamped):
    """Остаток = факт. Общий склад переиспользуется между бизнесами (§9.1)."""
    __tablename__ = "warehouse_stock"
    business_id = Column(String(36), nullable=False, index=True)
    nomenclature_id = Column(String(36), ForeignKey("nomenclature.id"), nullable=False, index=True)
    qty = Column(Numeric(18, 3), nullable=False, default=0)
    status = Column(String(16), nullable=False, default="on_stock")
    __table_args__ = (
        UniqueConstraint("business_id", "nomenclature_id", "status", name="uq_stock"),
    )


class WarehouseMovement(Base, UUIDPk, Timestamped):
    """Append-only движение склада (приход/расход/списание в производство)."""
    __tablename__ = "warehouse_movements"
    business_id = Column(String(36), nullable=False, index=True)
    nomenclature_id = Column(String(36), nullable=False, index=True)
    qty = Column(Numeric(18, 3), nullable=False)   # + приход / − расход
    kind = Column(String(32), nullable=False)      # receipt/issue/production/shipment/inventory/reversal
    from_status = Column(String(16), nullable=True)
    to_status = Column(String(16), nullable=True)
    basis_ref = Column(String(200), nullable=True)
    is_reversal = Column(Boolean, default=False, nullable=False)
    reversal_of = Column(String(36), nullable=True)


class ShippingTicket(Base, UUIDPk, Timestamped):
    """Цифровой талон отгрузки. Отгрузка ≠ приём денег (§9.3, разные логины §7.6)."""
    __tablename__ = "shipping_tickets"
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True, index=True)
    business_id = Column(String(36), nullable=False, index=True)
    vehicle = Column(String(100), nullable=True)
    driver_user_id = Column(String(36), nullable=True)
    nomenclature_id = Column(String(36), nullable=True)
    qty = Column(Numeric(18, 3), nullable=True)
    shipped_by = Column(String(36), nullable=False)   # кто отгрузил
    status = Column(String(16), nullable=False, default="shipped")


class ProductionTask(Base, UUIDPk, Timestamped):
    __tablename__ = "production_tasks"
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True, index=True)
    business_id = Column(String(36), nullable=False, index=True)
    recipe_id = Column(String(36), nullable=True)
    qty = Column(Numeric(18, 3), nullable=True)
    cost_frozen = Column(MONEY, nullable=True)     # себестоимость на дату
    status = Column(String(16), nullable=False, default="new")


class Delivery(Base, UUIDPk, Timestamped):
    __tablename__ = "deliveries"
    ticket_id = Column(String(36), ForeignKey("shipping_tickets.id"), nullable=True)
    business_id = Column(String(36), nullable=False, index=True)
    driver_user_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default="planned")
    note = Column(Text, nullable=True)


class Vehicle(Base, UUIDPk, Timestamped):
    __tablename__ = "vehicles"
    business_id = Column(String(36), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    kind = Column(String(64), nullable=True)   # миксер/самосвал/экскаватор/дробилка
    plate = Column(String(32), nullable=True)


class QualityPass(Base, UUIDPk, Timestamped):
    """Паспорт качества / рассев; испытание 7/28 дней (§9.3)."""
    __tablename__ = "quality_passes"
    business_id = Column(String(36), nullable=False, index=True)
    order_id = Column(String(36), nullable=True)
    sample_ref = Column(String(120), nullable=True)
    test_day = Column(Integer, nullable=True)   # 7 / 28
    result = Column(String(200), nullable=True)
    passed = Column(Boolean, nullable=True)


# ======================================================================
#  СНАБЖЕНИЕ (§9.5, §10)
# ======================================================================
class Supplier(Base, UUIDPk, Timestamped):
    __tablename__ = "suppliers"
    counterparty_id = Column(String(36), ForeignKey("counterparties.id"), nullable=False)
    rating = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)


class SupplyRequest(Base, UUIDPk, Timestamped):
    """Заявка на закупку от любого бизнеса (с пометкой чей расход)."""
    __tablename__ = "supply_requests"
    business_id = Column(String(36), nullable=False, index=True)  # чей расход
    items_json = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="new")
    note = Column(Text, nullable=True)


class Quote(Base, UUIDPk, Timestamped):
    """КП поставщика для сравнения."""
    __tablename__ = "quotes"
    request_id = Column(String(36), ForeignKey("supply_requests.id"), nullable=True, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=True)
    amount = Column(MONEY, nullable=False)
    items_json = Column(JSON, nullable=True)
    chosen = Column(Boolean, default=False, nullable=False)


class Limit(Base, UUIDPk, Timestamped):
    """Лимиты закупок; меняют только владельцы (§8.4)."""
    __tablename__ = "limits"
    business_id = Column(String(36), nullable=True, index=True)
    resource = Column(String(64), nullable=True)
    amount = Column(MONEY, nullable=False)
    set_by = Column(String(36), nullable=False)


class Purchase(Base, UUIDPk, Timestamped):
    """Закупка. В лимите — сам; крупно → согласование троих (§9.5)."""
    __tablename__ = "purchases"
    request_id = Column(String(36), ForeignKey("supply_requests.id"), nullable=True)
    supplier_id = Column(String(36), nullable=True)
    business_id = Column(String(36), nullable=False, index=True)
    amount = Column(MONEY, nullable=False)
    status = Column(String(32), nullable=False, default="new")
    limit_ok = Column(Boolean, default=True, nullable=False)
    approval_ref = Column(String(36), nullable=True)


class Receipt(Base, UUIDPk, Timestamped):
    """Оприходование на склад бизнеса → синхронизация склада (§9.5, §6.3)."""
    __tablename__ = "receipts"
    purchase_id = Column(String(36), ForeignKey("purchases.id"), nullable=True)
    business_id = Column(String(36), nullable=False, index=True)   # склад какого бизнеса
    nomenclature_id = Column(String(36), nullable=False)
    qty = Column(Numeric(18, 3), nullable=False)
    shortage = Column(Numeric(18, 3), nullable=True)  # недобор
    surplus = Column(Numeric(18, 3), nullable=True)   # перебор
    note = Column(Text, nullable=True)


class Approval(Base, UUIDPk, Timestamped):
    """Согласование крупного — цифровое «добро/нет» от всех троих (§8.2)."""
    __tablename__ = "approvals"
    kind = Column(String(64), nullable=False)   # purchase / expense / ...
    ref_id = Column(String(36), nullable=True)  # на что согласование
    amount = Column(MONEY, nullable=True)
    sohib = Column(String(8), nullable=True)     # yes/no/null
    iftikhor = Column(String(8), nullable=True)
    dovud = Column(String(8), nullable=True)
    result = Column(String(16), nullable=False, default="pending")
    note = Column(Text, nullable=True)


# ======================================================================
#  ЗАСТРОЙЩИК (§9.1)
# ======================================================================
class ConstructionObject(Base, UUIDPk, Timestamped):
    __tablename__ = "construction_objects"
    business_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    address = Column(String(300), nullable=True)
    city = Column(String(120), nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="active")


class Estimate(Base, UUIDPk, Timestamped):
    """Смета объекта, заморожена на дату (план/факт) (§9.1)."""
    __tablename__ = "estimates"
    object_id = Column(String(36), ForeignKey("construction_objects.id"), nullable=False, index=True)
    plan_json = Column(JSON, nullable=True)     # замороженный план
    plan_amount = Column(MONEY, nullable=True)
    fact_amount = Column(MONEY, nullable=False, default=0)
    frozen_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)


class Inventory(Base, UUIDPk, Timestamped):
    __tablename__ = "inventories"
    business_id = Column(String(36), nullable=False, index=True)
    object_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default="open")  # с блокировкой при пересчёте
    result_json = Column(JSON, nullable=True)


# ======================================================================
#  ПРОЕКТНАЯ КОМПАНИЯ (§9.2)
# ======================================================================
class Client(Base, UUIDPk, Timestamped):
    """Регистрация клиента обязательна (закон РТ) (§9.2)."""
    __tablename__ = "clients"
    counterparty_id = Column(String(36), nullable=True)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(64), nullable=True)
    registered = Column(Boolean, default=False, nullable=False)


class Brief(Base, UUIDPk, Timestamped):
    """Бриф с живым расчётом; цена заморожена (§9.2)."""
    __tablename__ = "briefs"
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True, index=True)
    params_json = Column(JSON, nullable=True)
    price_frozen = Column(MONEY, nullable=True)


class Contract(Base, UUIDPk, Timestamped):
    """Договор с графиком 50/30/20 (§9.2)."""
    __tablename__ = "contracts"
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True, index=True)
    brief_id = Column(String(36), nullable=True)
    amount = Column(MONEY, nullable=False)
    schedule_json = Column(JSON, nullable=True)  # 50/30/20
    status = Column(String(32), nullable=False, default="active")


class Project(Base, UUIDPk, Timestamped):
    __tablename__ = "projects"
    contract_id = Column(String(36), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    status = Column(String(32), nullable=False, default="active")


class Stage(Base, UUIDPk, Timestamped):
    """Этапы: генплан→эскиз→конструктив→сдача (§9.2)."""
    __tablename__ = "stages"
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    order_index = Column(Integer, default=0)
    status = Column(String(32), nullable=False, default="pending")


class SupervisionObject(Base, UUIDPk, Timestamped):
    """Авторский надзор (~47 объектов) (§9.2)."""
    __tablename__ = "supervision_objects"
    name = Column(String(200), nullable=False)
    manager_user_id = Column(String(36), nullable=True)
    monthly_fee = Column(MONEY, nullable=True)


class SupervisionRound(Base, UUIDPk, Timestamped):
    """Обход с фото, подтверждение этапа (§9.2)."""
    __tablename__ = "supervision_rounds"
    supervision_object_id = Column(String(36), ForeignKey("supervision_objects.id"), nullable=False, index=True)
    photos_json = Column(JSON, nullable=True)
    confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_by = Column(String(36), nullable=True)


class SupervisionPayment(Base, UUIDPk, Timestamped):
    __tablename__ = "supervision_payments"
    supervision_object_id = Column(String(36), nullable=False, index=True)
    period = Column(String(7), nullable=False)
    amount = Column(MONEY, nullable=False)
    collected_by = Column(String(36), nullable=True)


class GeodesyRequest(Base, UUIDPk, Timestamped):
    """Геодезия (Хушбахт) — отдельная услуга (§9.2)."""
    __tablename__ = "geodesy_requests"
    client_id = Column(String(36), nullable=True)
    amount = Column(MONEY, nullable=True)
    status = Column(String(32), nullable=False, default="new")


# ======================================================================
#  ЩЕБЁНОЧНЫЙ ЗАВОД (§9.4)
# ======================================================================
class Fraction(Base, UUIDPk, Timestamped):
    """Каталог: песок, щебень, пудра, зубок, смесь (§9.4)."""
    __tablename__ = "fractions"
    business_id = Column(String(36), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    unit_id = Column(String(36), nullable=True)


class ProductionShift(Base, UUIDPk, Timestamped):
    __tablename__ = "production_shifts"
    business_id = Column(String(36), nullable=False, index=True)
    shift_date = Column(Date, default=date.today, nullable=False)
    note = Column(Text, nullable=True)


class FractionOutput(Base, UUIDPk, Timestamped):
    """Выпуск по фракциям за смену (§9.4)."""
    __tablename__ = "fraction_outputs"
    shift_id = Column(String(36), ForeignKey("production_shifts.id"), nullable=False, index=True)
    fraction_id = Column(String(36), nullable=False)
    qty = Column(Numeric(18, 3), nullable=False)


class FuelConsumption(Base, UUIDPk, Timestamped):
    """Расход солярки по нормам на машину (§9.4)."""
    __tablename__ = "fuel_consumptions"
    business_id = Column(String(36), nullable=False, index=True)
    vehicle_id = Column(String(36), nullable=True)
    liters = Column(Numeric(18, 3), nullable=False)
    norm_liters = Column(Numeric(18, 3), nullable=True)
    shift_id = Column(String(36), nullable=True)


class CapacityRecord(Base, UUIDPk, Timestamped):
    """Мощность (факт выработки) (§9.4)."""
    __tablename__ = "capacity_records"
    business_id = Column(String(36), nullable=False, index=True)
    period = Column(String(7), nullable=False)
    output_qty = Column(Numeric(18, 3), nullable=True)
    cost_per_unit = Column(MONEY, nullable=True)  # себестоимость = расходы ÷ выпуск


# ======================================================================
#  ЗАДАЧИ / КАЛЕНДАРЬ / ВЛАДЕЛЬЦЫ (§9.7, §10)
# ======================================================================
class Task(Base, UUIDPk, Timestamped):
    __tablename__ = "tasks"
    assigned_to = Column(String(36), nullable=False, index=True)
    assigned_by = Column(String(36), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    business_scope = Column(String(36), nullable=True)  # зона задачи (для Довуда §8.2)
    due_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(16), nullable=False, default="open")


class CalendarEvent(Base, UUIDPk, Timestamped):
    __tablename__ = "calendar_events"
    owner_scope = Column(String(64), nullable=True)
    type = Column(String(32), nullable=True)  # задача/встреча/дедлайн
    title = Column(String(300), nullable=False)
    at = Column(DateTime(timezone=True), nullable=True)
    participants_json = Column(JSON, nullable=True)


# ======================================================================
#  ОТДЕЛ ПРОВЕРКИ (§9.8) — только чтение по данным систем
# ======================================================================
class InspectionPlan(Base, UUIDPk, Timestamped):
    __tablename__ = "inspection_plans"
    title = Column(String(200), nullable=False)
    scheduled_at = Column(Date, nullable=True)
    planned = Column(Boolean, default=True, nullable=False)  # план/внеплан


class InspectionAct(Base, UUIDPk, Timestamped):
    __tablename__ = "inspection_acts"
    plan_id = Column(String(36), nullable=True)
    business_id = Column(String(36), nullable=True)
    title = Column(String(200), nullable=False)
    status = Column(String(16), nullable=False, default="open")  # открыто/устранено
    summary = Column(Text, nullable=True)


class Remark(Base, UUIDPk, Timestamped):
    __tablename__ = "remarks"
    act_id = Column(String(36), ForeignKey("inspection_acts.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="open")


class Escalation(Base, UUIDPk, Timestamped):
    """Эскалация нарушения — всем троим владельцам, минуя зону нарушителя (§9.8)."""
    __tablename__ = "escalations"
    act_id = Column(String(36), nullable=True)
    remark_id = Column(String(36), nullable=True)
    reason = Column(Text, nullable=False)
    to_owners = Column(JSON, nullable=True)  # ['sohib','iftikhor','dovud']
    bypass_business = Column(String(36), nullable=True)


# ======================================================================
#  АУДИТ-ЛОГ (§7.7) — неизменяемый
# ======================================================================
class AuditLog(Base, UUIDPk):
    __tablename__ = "audit_log"
    user_id = Column(String(36), nullable=True, index=True)
    action = Column(String(64), nullable=False)
    resource = Column(String(64), nullable=False, index=True)
    ref_id = Column(String(36), nullable=True)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    at = Column(DateTime(timezone=True), default=now_utc, nullable=False, index=True)
