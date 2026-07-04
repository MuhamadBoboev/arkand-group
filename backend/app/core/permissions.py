"""RBAC-матрица (§8): каталог ролей и их permissions (resource, action, scope).

Доступ — не по «названию роли», а по набору permissions. Роль = набор permissions.
Проверка прав — на бэке (см. app/services/rbac.py и app/core/deps.py).
"""
from __future__ import annotations

from app.core.constants import Action as A
from app.core.constants import Business as B
from app.core.constants import Resource as R
from app.core.constants import Scope as S

# Ресурсы, к которым отдел проверки имеет read_only (§8.4, §9.8).
AUDITABLE_RESOURCES = [
    R.OBJECT, R.ORDER, R.CASH, R.INKASSACIYA, R.SUPPLY_REQUEST, R.PURCHASE,
    R.DEBT, R.RECIPE, R.WAREHOUSE, R.SHIPPING, R.SALARY, R.PERIOD,
    R.COUNTERPARTY, R.NOMENCLATURE, R.PROJECT, R.FRACTION, R.QUALITY, R.ANALYTICS,
]

_CRUD = [A.VIEW, A.CREATE, A.UPDATE_VIA_REVERSAL, A.REVERSE]


def _perms(pairs: list[tuple]) -> list[tuple[str, str, str]]:
    return [(r, a, s) for (r, a, s) in pairs]


# ROLE_DEFS: name -> (title, [(resource, action, scope)])
ROLE_DEFS: dict[str, dict] = {
    # --- Верхний уровень власти (§8.1) ---
    "owner_full": {
        "title": "Владелец — полный доступ",
        "permissions": [(R.ALL, A.ALL, S.ALL)],  # Сохиб, Ифтихор
    },
    "owner_project": {
        "title": "Владелец проектной зоны (Довуд)",
        "permissions": [
            # Полный доступ в зоне проектной
            (R.PROJECT, A.VIEW, S.OWN_BUSINESS), (R.PROJECT, A.CREATE, S.OWN_BUSINESS),
            (R.PROJECT, A.UPDATE_VIA_REVERSAL, S.OWN_BUSINESS),
            (R.ORDER, A.VIEW, S.OWN_BUSINESS), (R.ORDER, A.CREATE, S.OWN_BUSINESS),
            (R.CASH, A.VIEW, S.OWN_BUSINESS),
            (R.APPROVAL, A.APPROVE, S.ALL),          # согласует крупные расходы (все трое §8.2)
            (R.TASK, A.ASSIGN_TASK, S.OWN_BUSINESS), # ставит задачи в своей зоне
            (R.ANALYTICS, A.VIEW, S.OWN_BUSINESS),   # только своя зона; не общий раздел
        ],
    },

    # --- Финансы (§9.6) ---
    "chief_accountant": {
        "title": "Главный бухгалтер",
        "permissions": _perms([
            (R.CASH, a, S.ALL) for a in _CRUD
        ] + [
            (R.INKASSACIYA, A.VIEW, S.ALL), (R.INKASSACIYA, A.CONFIRM, S.ALL),
            (R.DEBT, A.VIEW, S.ALL), (R.DEBT, A.CREATE, S.ALL),
            (R.SALARY, A.VIEW, S.ALL), (R.SALARY, A.CREATE, S.ALL), (R.SALARY, A.CONFIRM, S.ALL),
            (R.PERIOD, A.VIEW, S.ALL), (R.PERIOD, A.CREATE, S.ALL),
            (R.ANALYTICS, A.VIEW, S.ALL),
        ]),
    },
    "accountant": {
        "title": "Бухгалтер",
        "permissions": [
            (R.CASH, A.VIEW, S.ALL), (R.CASH, A.CREATE, S.ALL), (R.CASH, A.CONFIRM, S.ALL),
            (R.INKASSACIYA, A.VIEW, S.ALL),
            (R.DEBT, A.VIEW, S.ALL),
            (R.SALARY, A.VIEW, S.ALL), (R.SALARY, A.CREATE, S.ALL),
        ],
    },
    "cashier": {
        "title": "Кассир (своя касса)",
        "permissions": [
            (R.CASH, A.VIEW, S.OWN_RECORDS), (R.CASH, A.CREATE, S.OWN_RECORDS),
            (R.INKASSACIYA, A.VIEW, S.OWN_RECORDS), (R.INKASSACIYA, A.CREATE, S.OWN_RECORDS),
        ],
    },
    "cash_receiver": {
        "title": "Получатель инкассации (директор/ответственный)",
        "permissions": [
            (R.INKASSACIYA, A.VIEW, S.ALL), (R.INKASSACIYA, A.CONFIRM, S.ALL),
        ],
    },

    # --- Снабжение (§9.5) ---
    "supply_team": {
        "title": "Команда снабжения",
        "permissions": [
            (R.SUPPLY_REQUEST, A.VIEW, S.ALL), (R.SUPPLY_REQUEST, A.CREATE, S.ALL),
            (R.PURCHASE, A.VIEW, S.ALL), (R.PURCHASE, A.CREATE, S.ALL),
            (R.WAREHOUSE, A.VIEW, S.ALL), (R.WAREHOUSE, A.CREATE, S.ALL),
            (R.COUNTERPARTY, A.VIEW, S.ALL), (R.COUNTERPARTY, A.CREATE, S.ALL),
            (R.NOMENCLATURE, A.VIEW, S.ALL), (R.NOMENCLATURE, A.CREATE, S.ALL),
            (R.DEBT, A.VIEW, S.ALL),
        ],
    },

    # --- Застройщик (§9.1) ---
    "foreman": {
        "title": "Прораб / объект",
        "permissions": [
            (R.OBJECT, A.VIEW, S.OWN_BUSINESS), (R.OBJECT, A.CREATE, S.OWN_BUSINESS),
            (R.SUPPLY_REQUEST, A.CREATE, S.OWN_BUSINESS),
            (R.WAREHOUSE, A.VIEW, S.OWN_BUSINESS),
        ],
    },
    "sales_manager": {
        "title": "Менеджер по продажам (не видит расходы)",
        "permissions": [
            (R.ORDER, A.VIEW, S.OWN_BUSINESS), (R.ORDER, A.CREATE, S.OWN_BUSINESS),
            # НЕТ доступа к CASH/расходам (§9.1)
        ],
    },
    "storekeeper": {
        "title": "Кладовщик",
        "permissions": [
            (R.WAREHOUSE, A.VIEW, S.OWN_BUSINESS), (R.WAREHOUSE, A.CREATE, S.OWN_BUSINESS),
        ],
    },

    # --- Заводы (§9.3, §9.4) ---
    "operator": {
        "title": "Оператор завода (производство/отгрузка — без денег)",
        "permissions": [
            (R.ORDER, A.VIEW, S.OWN_BUSINESS), (R.ORDER, A.CREATE, S.OWN_BUSINESS),
            (R.SHIPPING, A.VIEW, S.OWN_BUSINESS), (R.SHIPPING, A.CREATE, S.OWN_BUSINESS),
            (R.WAREHOUSE, A.VIEW, S.OWN_BUSINESS),
            (R.RECIPE, A.VIEW, S.OWN_BUSINESS),
            (R.FRACTION, A.VIEW, S.OWN_BUSINESS), (R.FRACTION, A.CREATE, S.OWN_BUSINESS),
            (R.QUALITY, A.VIEW, S.OWN_BUSINESS), (R.QUALITY, A.CREATE, S.OWN_BUSINESS),
            # НЕТ доступа к деньгам (отгрузка ≠ касса §7.6)
        ],
    },
    "driver": {
        "title": "Шофёр (личный кабинет)",
        "permissions": [
            (R.SHIPPING, A.VIEW, S.OWN_RECORDS),
        ],
    },
    "mechanic": {
        "title": "Механик",
        "permissions": [
            (R.SHIPPING, A.VIEW, S.OWN_BUSINESS),
        ],
    },

    # --- Проектная (§9.2) ---
    "architect": {
        "title": "Гл. архитектор / руководитель",
        "permissions": [
            (R.PROJECT, A.VIEW, S.OWN_BUSINESS), (R.PROJECT, A.CREATE, S.OWN_BUSINESS),
            (R.PROJECT, A.UPDATE_VIA_REVERSAL, S.OWN_BUSINESS),
            (R.ORDER, A.VIEW, S.OWN_BUSINESS), (R.ORDER, A.CREATE, S.OWN_BUSINESS),
            (R.CASH, A.VIEW, S.OWN_BUSINESS),
        ],
    },
    "designer": {
        "title": "Проектировщик (свой раздел, без финансов)",
        "permissions": [
            (R.PROJECT, A.VIEW, S.OWN_BUSINESS), (R.PROJECT, A.CREATE, S.OWN_BUSINESS),
        ],
    },

    # --- Отдел проверки (§9.8) — только чтение ---
    "auditor": {
        "title": "Ревизор (отдел проверки, read-only)",
        # read_only к данным ВСЕХ систем; собственные акты/замечания/эскалации — свой домен (scope all)
        "permissions": [(res, A.VIEW, S.READ_ONLY) for res in AUDITABLE_RESOURCES] + [
            (R.AUDIT, A.VIEW, S.ALL), (R.AUDIT, A.CREATE, S.ALL),
        ],
    },
    "audit_head": {
        "title": "Руководитель отдела проверки",
        "permissions": [(res, A.VIEW, S.READ_ONLY) for res in AUDITABLE_RESOURCES] + [
            (R.AUDIT, A.VIEW, S.ALL), (R.AUDIT, A.CREATE, S.ALL),
        ],
    },
}


def all_permission_tuples() -> set[tuple[str, str, str]]:
    """Все уникальные permissions из каталога — для сидинга таблицы permissions."""
    out: set[tuple[str, str, str]] = set()
    for role in ROLE_DEFS.values():
        for p in role["permissions"]:
            out.add(tuple(p))
    return out
