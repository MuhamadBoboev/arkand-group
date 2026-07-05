"""Глубокий тест ПО КАЖДОЙ РОЛИ отдельно: возможности (доступно) и ограничения (запрещено).

Изолированная БД (test_roles.db). Запуск:
  DATABASE_URL=sqlite:///./test_roles.db python -m tests.test_roles
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from app.main import app
from app.seed import run as seed

# Свежая изолированная БД
from app.db.base import Base, engine
Base.metadata.drop_all(bind=engine)
seed()

client = TestClient(app)

PASS = 0
FAIL = 0
FAILURES: list[str] = []
_tok: dict[str, str] = {}


def login(phone: str) -> str:
    if phone not in _tok:
        r = client.post("/api/auth/login", json={"phone": phone, "password": "arkand"})
        _tok[phone] = r.json()["access_token"]
    return _tok[phone]


def H(phone: str):
    return {"Authorization": f"Bearer {login(phone)}"}


def call(phone: str, method: str, path: str, body=None):
    return client.request(method, path, headers=H(phone), json=body)


def allow(role: str, phone: str, method: str, path: str, body=None):
    """Ожидаем доступ (2xx)."""
    global PASS, FAIL
    r = call(phone, method, path, body)
    ok = r.status_code in (200, 201)
    _record(ok, f"[{role}] МОЖЕТ {method} {path}", r)


def deny(role: str, phone: str, method: str, path: str, body=None):
    """Ожидаем запрет (403)."""
    global PASS, FAIL
    r = call(phone, method, path, body)
    ok = r.status_code == 403
    _record(ok, f"[{role}] НЕ может {method} {path} (403)", r)


def _record(ok: bool, name: str, r):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name} :: got {r.status_code} {r.text[:120]}")


SOHIB, IFTIKHOR, DOVUD = "+992900000001", "+992900000002", "+992900000003"
CASHIER, SUPPLY, AUDITOR = "+992900000010", "+992900000011", "+992900000012"
CHIEF, OPERATOR, RECEIVER = "+992900000013", "+992900000014", "+992900000015"
SALES, ARCHITECT, FOREMAN = "+992900000016", "+992900000017", "+992900000018"


def own_cash_id(phone: str) -> str:
    items = call(phone, "GET", "/api/finance/cash").json()["items"]
    return items[0]["id"]


def main() -> None:
    print("\n########## ГЛУБОКИЙ ТЕСТ ПО РОЛЯМ ##########")

    # ===== ВЛАДЕЛЬЦЫ (Сохиб/Ифтихор) — полный доступ =====
    for who, nm in ((SOHIB, "Сохиб"), (IFTIKHOR, "Ифтихор")):
        print(f"\n=== {nm} (владелец, полный доступ) ===")
        allow(nm, who, "GET", "/api/owners/employees")
        allow(nm, who, "GET", "/api/owners/analytics/summary")
        allow(nm, who, "GET", "/api/owners/calendar")
        allow(nm, who, "GET", "/api/audit/log")
        allow(nm, who, "GET", "/api/finance/cash")
        allow(nm, who, "POST", "/api/finance/cash", {"name": "Касса " + nm, "business_id": "beton"})
        allow(nm, who, "GET", "/api/supply/requests")

    # ===== Довуд (проектная зона) =====
    print("\n=== Довуд (проектная зона) ===")
    allow("Довуд", DOVUD, "GET", "/api/proektnaya/projects")
    allow("Довуд", DOVUD, "POST", "/api/proektnaya/projects", {"title": "Проект Д"})
    allow("Довуд", DOVUD, "GET", "/api/owners/approvals")
    allow("Довуд", DOVUD, "GET", "/api/owners/tasks")
    deny("Довуд", DOVUD, "GET", "/api/owners/employees")          # раздел только Сохиб/Ифтихор
    deny("Довуд", DOVUD, "GET", "/api/owners/analytics/summary")  # раздел только Сохиб/Ифтихор
    deny("Довуд", DOVUD, "GET", "/api/owners/calendar")
    deny("Довуд", DOVUD, "POST", "/api/finance/cash", {"name": "x", "business_id": "proektnaya"})
    deny("Довуд", DOVUD, "GET", "/api/audit/log")
    deny("Довуд", DOVUD, "GET", "/api/zastroyshchik/objects?business_id=zastroyshchik")  # чужой бизнес

    # ===== Кассир =====
    print("\n=== Кассир (своя касса) ===")
    allow("Кассир", CASHIER, "GET", "/api/finance/cash")
    allow("Кассир", CASHIER, "GET", "/api/inkassaciya")
    cid = own_cash_id(CASHIER)
    allow("Кассир", CASHIER, "POST", "/api/finance/movements", {"cash_id": cid, "kind": "income", "amount": 1000, "article": "Продажа"})
    allow("Кассир", CASHIER, "POST", "/api/inkassaciya/start", {"cash_id": cid})
    deny("Кассир", CASHIER, "GET", "/api/owners/employees")
    deny("Кассир", CASHIER, "POST", "/api/finance/cash", {"name": "x", "business_id": "zastroyshchik"})
    deny("Кассир", CASHIER, "GET", "/api/audit/log")
    deny("Кассир", CASHIER, "GET", "/api/supply/requests")
    deny("Кассир", CASHIER, "GET", "/api/owners/approvals")

    # ===== Снабженец =====
    print("\n=== Снабженец ===")
    allow("Снабженец", SUPPLY, "GET", "/api/supply/requests")
    allow("Снабженец", SUPPLY, "POST", "/api/supply/requests", {"business_id": "beton", "items": [{"name": "Цемент", "qty": 5}]})
    allow("Снабженец", SUPPLY, "GET", "/api/supply/purchases")
    allow("Снабженец", SUPPLY, "POST", "/api/supply/purchases", {"business_id": "beton", "amount": 5000})
    allow("Снабженец", SUPPLY, "GET", "/api/nomenclature")
    allow("Снабженец", SUPPLY, "GET", "/api/counterparties")
    deny("Снабженец", SUPPLY, "POST", "/api/finance/cash", {"name": "x", "business_id": "beton"})
    deny("Снабженец", SUPPLY, "GET", "/api/owners/employees")
    deny("Снабженец", SUPPLY, "GET", "/api/inkassaciya")
    deny("Снабженец", SUPPLY, "GET", "/api/audit/log")

    # ===== Ревизор (read-only) =====
    print("\n=== Ревизор (отдел проверки, read-only) ===")
    allow("Ревизор", AUDITOR, "GET", "/api/audit/log")
    allow("Ревизор", AUDITOR, "GET", "/api/audit/reconcile/cash")
    allow("Ревизор", AUDITOR, "POST", "/api/audit/acts", {"title": "Проверка касс"})
    allow("Ревизор", AUDITOR, "GET", "/api/finance/cash")       # read-only чтение
    allow("Ревизор", AUDITOR, "GET", "/api/inkassaciya")
    deny("Ревизор", AUDITOR, "POST", "/api/finance/cash", {"name": "x", "business_id": "beton"})
    deny("Ревизор", AUDITOR, "GET", "/api/owners/employees")
    deny("Ревизор", AUDITOR, "GET", "/api/owners/analytics/summary")  # раздел только Сохиб/Ифтихор

    # ===== Главбух =====
    print("\n=== Главный бухгалтер ===")
    allow("Главбух", CHIEF, "GET", "/api/finance/cash")
    allow("Главбух", CHIEF, "POST", "/api/finance/cash", {"name": "Касса ГБ", "business_id": "finance"})
    allow("Главбух", CHIEF, "GET", "/api/finance/debts")
    allow("Главбух", CHIEF, "GET", "/api/finance/salaries")
    allow("Главбух", CHIEF, "POST", "/api/finance/period/close", {"business_id": "beton", "period": "2020-01"})
    deny("Главбух", CHIEF, "GET", "/api/owners/employees")
    deny("Главбух", CHIEF, "GET", "/api/audit/log")
    deny("Главбух", CHIEF, "POST", "/api/supply/requests", {"business_id": "beton", "items": []})

    # ===== Оператор завода =====
    print("\n=== Оператор бетонного завода (без денег) ===")
    allow("Оператор", OPERATOR, "GET", "/api/beton/orders")
    allow("Оператор", OPERATOR, "POST", "/api/beton/orders", {"mark": "M300", "volume": 5, "amount": 3000})
    allow("Оператор", OPERATOR, "POST", "/api/beton/shipping", {"vehicle": "A100", "qty": 5})
    allow("Оператор", OPERATOR, "GET", "/api/beton/stock")
    deny("Оператор", OPERATOR, "POST", "/api/finance/cash", {"name": "x", "business_id": "beton"})
    deny("Оператор", OPERATOR, "GET", "/api/owners/employees")
    deny("Оператор", OPERATOR, "GET", "/api/audit/log")
    deny("Оператор", OPERATOR, "GET", "/api/shcheben/fractions?business_id=shcheben")  # чужой бизнес

    # ===== Директор (приём инкассации) =====
    print("\n=== Директор (приём инкассации) ===")
    allow("Директор", RECEIVER, "GET", "/api/inkassaciya")
    deny("Директор", RECEIVER, "POST", "/api/finance/cash", {"name": "x", "business_id": "beton"})
    deny("Директор", RECEIVER, "POST", "/api/inkassaciya/start", {"cash_id": cid})  # нет права create
    deny("Директор", RECEIVER, "GET", "/api/owners/employees")
    deny("Директор", RECEIVER, "GET", "/api/audit/log")

    # ===== Менеджер продаж (не видит расходы) =====
    print("\n=== Менеджер продаж ===")
    deny("Продажи", SALES, "POST", "/api/finance/cash", {"name": "x", "business_id": "zastroyshchik"})
    deny("Продажи", SALES, "GET", "/api/owners/employees")
    deny("Продажи", SALES, "GET", "/api/audit/log")
    deny("Продажи", SALES, "GET", "/api/beton/orders")  # чужой бизнес (его зона — застройщик)

    # ===== Архитектор =====
    print("\n=== Архитектор ===")
    allow("Архитектор", ARCHITECT, "GET", "/api/proektnaya/projects")
    allow("Архитектор", ARCHITECT, "POST", "/api/proektnaya/projects", {"title": "Проект А"})
    allow("Архитектор", ARCHITECT, "GET", "/api/finance/cash")  # видит кассу своей зоны
    deny("Архитектор", ARCHITECT, "GET", "/api/owners/employees")
    deny("Архитектор", ARCHITECT, "GET", "/api/audit/log")
    deny("Архитектор", ARCHITECT, "GET", "/api/zastroyshchik/objects?business_id=zastroyshchik")

    # ===== Прораб =====
    print("\n=== Прораб ===")
    allow("Прораб", FOREMAN, "GET", "/api/zastroyshchik/objects?business_id=zastroyshchik")
    allow("Прораб", FOREMAN, "POST", "/api/zastroyshchik/objects", {"name": "Объект П", "business_id": "zastroyshchik"})
    allow("Прораб", FOREMAN, "POST", "/api/supply/requests", {"business_id": "zastroyshchik", "items": [{"name": "Кирпич", "qty": 100}]})
    allow("Прораб", FOREMAN, "GET", "/api/zastroyshchik/stock?business_id=zastroyshchik")
    deny("Прораб", FOREMAN, "GET", "/api/beton/orders")          # чужой бизнес
    deny("Прораб", FOREMAN, "GET", "/api/owners/employees")
    deny("Прораб", FOREMAN, "POST", "/api/finance/cash", {"name": "x", "business_id": "zastroyshchik"})
    deny("Прораб", FOREMAN, "GET", "/api/audit/log")

    # ===== Валидация ввода (числовые поля не принимают буквы) =====
    print("\n=== Валидация ввода ===")
    r = call(OPERATOR, "POST", "/api/beton/orders", {"mark": "M300", "volume": "буквы", "amount": 3000})
    _record(r.status_code == 400, "[Валидация] буквы в volume -> 400", r)
    r = call(SUPPLY, "POST", "/api/supply/purchases", {"business_id": "beton", "amount": -5})
    _record(r.status_code in (400, 422), "[Валидация] отрицательная сумма закупки -> 400/422", r)
    r = call(CASHIER, "POST", "/api/finance/movements", {"cash_id": cid, "kind": "income", "amount": 0})
    _record(r.status_code in (400, 422), "[Валидация] нулевая сумма проводки -> 400/422", r)
    r = client.post("/api/auth/login", json={"phone": SOHIB, "password": "wrong"})
    _record(r.status_code == 401, "[Безопасность] неверный пароль -> 401", r)
    r = client.get("/api/finance/cash")  # без токена
    _record(r.status_code == 401, "[Безопасность] без токена -> 401", r)

    print(f"\n################  ИТОГО ПО РОЛЯМ: PASS={PASS}  FAIL={FAIL}  ################")
    if FAIL:
        print("Провалы:")
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)
    print("ВСЕ РОЛЕВЫЕ ПРОВЕРКИ ПРОЙДЕНЫ.")


if __name__ == "__main__":
    main()
