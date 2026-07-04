"""Единые константы статусов и типов (§7.4, §8). Свободный текст в статусах запрещён."""
from __future__ import annotations


class Business:
    """Типы бизнесов холдинга (§1). Снабжение/Финансы — общие сервисы."""
    ZASTROYSHCHIK = "zastroyshchik"
    PROEKTNAYA = "proektnaya"
    BETON = "beton"
    SHCHEBEN = "shcheben"
    SUPPLY = "supply"
    FINANCE = "finance"
    OWNERS = "owners"
    AUDIT = "audit"
    ALL = [ZASTROYSHCHIK, PROEKTNAYA, BETON, SHCHEBEN, SUPPLY, FINANCE, OWNERS, AUDIT]


class OwnerType:
    SOHIB = "sohib"        # Главный финансист
    IFTIKHOR = "iftikhor"  # Суперадмин
    DOVUD = "dovud"        # Проектная компания
    ALL = [SOHIB, IFTIKHOR, DOVUD]


class MoneyKind:
    INCOME = "income"    # доход (+)
    EXPENSE = "expense"  # расход (−)


class MoneyStatus:
    """Статусы денег (§7.4)."""
    IN_CASH = "in_cash"          # в_кассе
    IN_TRANSIT = "in_transit"    # в_пути
    ACCEPTED = "accepted"        # принято
    DISCREPANCY = "discrepancy"  # расхождение


class IncomeStage:
    """Доход: аванс(обязательство) → отработано → выручка (§7.4)."""
    ADVANCE = "advance"      # аванс = обязательство, НЕ выручка
    WORKED = "worked"        # отработано
    REVENUE = "revenue"      # выручка


class InkassaciyaStatus:
    """Инкассация (§9.6.1): в_кассе → в_пути → принято + расхождение."""
    IN_CASH = "in_cash"
    IN_TRANSIT = "in_transit"
    ACCEPTED = "accepted"
    DISCREPANCY = "discrepancy"


class OrderStatus:
    """Заказ (§7.2 — обратные потоки штатные)."""
    NEW = "new"
    IN_PRODUCTION = "in_production"
    SHIPPED = "shipped"
    DONE = "done"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    PARTIAL = "partial"      # выполнен_частично
    DEFECT = "defect"        # брак


class StockStatus:
    """Сырьё: на_складе → в_производстве → в_готовом → отгружено (§7.4)."""
    ON_STOCK = "on_stock"
    IN_PRODUCTION = "in_production"
    IN_FINISHED = "in_finished"
    SHIPPED = "shipped"


class DebtStatus:
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"


class ApprovalResult:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Decision:
    YES = "yes"
    NO = "no"


class TaskStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class ActStatus:
    OPEN = "open"        # открыто
    RESOLVED = "resolved"  # устранено


class Scope:
    """Область видимости permission (§8.5)."""
    ALL = "all"
    OWN_BUSINESS = "own_business"    # own_business:<id>
    OWN_RECORDS = "own_records"
    READ_ONLY = "read_only"


class Resource:
    OBJECT = "object"
    ORDER = "order"
    CASH = "cash"
    INKASSACIYA = "inkassaciya"
    SUPPLY_REQUEST = "supply_request"
    PURCHASE = "purchase"
    APPROVAL = "approval"
    EMPLOYEE = "employee"
    ANALYTICS = "analytics"
    CALENDAR = "calendar"
    TASK = "task"
    DEBT = "debt"
    RECIPE = "recipe"
    WAREHOUSE = "warehouse"
    SHIPPING = "shipping"
    SALARY = "salary"
    PERIOD = "period"
    AUDIT = "audit"
    COUNTERPARTY = "counterparty"
    NOMENCLATURE = "nomenclature"
    PROJECT = "project"
    FRACTION = "fraction"
    QUALITY = "quality"
    ACCESS = "access"
    ALL = "*"  # полный доступ (владельцы)


class Action:
    VIEW = "view"
    CREATE = "create"
    UPDATE_VIA_REVERSAL = "update_via_reversal"
    REVERSE = "reverse"
    CONFIRM = "confirm"
    APPROVE = "approve"
    DISABLE_ACCESS = "disable_access"
    ASSIGN_TASK = "assign_task"
    ALL = "*"
