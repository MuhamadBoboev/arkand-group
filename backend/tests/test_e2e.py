"""Сквозной E2E-тест ARKAND CRM по всем ролям и правилам ТЗ.

Запуск:  python -m tests.test_e2e   (из каталога backend, при засеянной arkand.db)
Проверяет: auth, RBAC-запреты (§8), scope, инкассацию (§9.6.1), append-only сторно (§7.1),
согласование троих (§8.2), защиту владельцев (§8.2), разделы только Сохиб/Ифтихор (§8.3),
автосписание сырья по рецептуре (§9.3), отдел проверки read-only (§9.8).
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        FAILURES.append(f"{name} :: {detail}")
        print(f"  [FAIL] {name} :: {detail}")


_tokens: dict[str, str] = {}


def login(phone: str, password: str = "arkand") -> str:
    if phone in _tokens:
        return _tokens[phone]
    r = client.post("/api/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, f"login {phone}: {r.text}"
    tok = r.json()["access_token"]
    _tokens[phone] = tok
    return tok


def H(phone: str) -> dict:
    return {"Authorization": f"Bearer {login(phone)}"}


# Телефоны демо-ролей
SOHIB, IFTIKHOR, DOVUD = "+992900000001", "+992900000002", "+992900000003"
CASHIER, SUPPLY, AUDITOR = "+992900000010", "+992900000011", "+992900000012"
CHIEF, OPERATOR, RECEIVER = "+992900000013", "+992900000014", "+992900000015"
SALES, ARCHITECT = "+992900000016", "+992900000017"
FOREMAN = "+992900000018"


def user_ids() -> dict[str, str]:
    r = client.get("/api/users", headers=H(SOHIB))
    return {u["phone"]: u["id"] for u in r.json()}


def main() -> None:
    print("\n=== 1. Health + Auth (§14) ===")
    check("health ok", client.get("/health").json().get("status") == "ok")
    check("owner login ok", client.post("/api/auth/login", json={"phone": SOHIB, "password": "arkand"}).status_code == 200)
    check("wrong password rejected 401", client.post("/api/auth/login", json={"phone": SOHIB, "password": "x"}).status_code == 401)
    check("no token -> 401", client.get("/api/auth/me").status_code == 401)

    me = client.get("/api/auth/me", headers=H(SOHIB)).json()
    check("me: Sohib is owner", me["is_owner"] and me["owner_type"] == "sohib", str(me))

    ids = user_ids()

    print("\n=== 2. RBAC-запреты (§8) ===")
    check("cashier cannot list employees (403)", client.get("/api/owners/employees", headers=H(CASHIER)).status_code == 403)
    check("auditor cannot create cash (403)", client.post("/api/finance/cash", headers=H(AUDITOR), json={"name": "x", "business_id": "beton"}).status_code == 403)
    # sales_manager не имеет прав на кассу -> список пуст (§9.1 — не видит расходы)
    sc = client.get("/api/finance/cash", headers=H(SALES))
    check("sales sees no cash (empty)", sc.status_code == 200 and sc.json()["total"] == 0, sc.text)

    print("\n=== 3. Разделы только Сохиб/Ифтихор (§8.3) ===")
    check("Dovud denied employees section (403)", client.get("/api/owners/employees", headers=H(DOVUD)).status_code == 403)
    check("Dovud denied analytics section (403)", client.get("/api/owners/analytics/summary", headers=H(DOVUD)).status_code == 403)
    check("Sohib allowed employees section (200)", client.get("/api/owners/employees", headers=H(SOHIB)).status_code == 200)
    check("Iftikhor allowed calendar section (200)", client.get("/api/owners/calendar", headers=H(IFTIKHOR)).status_code == 200)

    print("\n=== 4. Финансы: касса кассира + scope (§8.4) ===")
    # Сохиб создаёт кассу с ответственным кассиром
    cash = client.post("/api/finance/cash", headers=H(SOHIB), json={
        "name": "Тест-касса", "business_id": "zastroyshchik", "responsible_user_id": ids[CASHIER]}).json()
    cash_id = cash["id"]
    # Кассир пополняет свою кассу
    r1 = client.post("/api/finance/movements", headers=H(CASHIER), json={"cash_id": cash_id, "kind": "income", "amount": 20000, "article": "Продажа"})
    check("cashier income on own cash 201", r1.status_code == 201, r1.text)
    bal = client.get(f"/api/finance/cash/{cash_id}/balance", headers=H(CASHIER)).json()
    check("balance = 20000", bal["balance"] in ("20000.00", "20000"), str(bal))
    # Кассир НЕ может писать в чужую кассу (бетон)
    beton_cash = client.post("/api/finance/cash", headers=H(SOHIB), json={"name": "Касса2", "business_id": "beton"}).json()
    rx = client.post("/api/finance/movements", headers=H(CASHIER), json={"cash_id": beton_cash["id"], "kind": "income", "amount": 100})
    check("cashier denied foreign cash (403)", rx.status_code == 403, rx.text)

    print("\n=== 5. Append-only сторно (§7.1) ===")
    mv = client.post("/api/finance/movements", headers=H(CASHIER), json={"cash_id": cash_id, "kind": "expense", "amount": 5000, "article": "Ошибка"}).json()
    rev = client.post(f"/api/finance/movements/{mv['id']}/reverse", headers=H(CHIEF), json={"reason": "исправление"})
    check("reversal created 201", rev.status_code == 201, rev.text)
    bal2 = client.get(f"/api/finance/cash/{cash_id}/balance", headers=H(CASHIER)).json()
    check("balance restored to 20000 after reversal", bal2["balance"] in ("20000.00", "20000"), str(bal2))
    rev2 = client.post(f"/api/finance/movements/{mv['id']}/reverse", headers=H(CHIEF), json={"reason": "again"})
    check("double reversal blocked 409", rev2.status_code == 409, rev2.text)

    print("\n=== 6. Инкассация двусторонняя (§9.6.1) ===")
    # Свежая касса для чистого сценария
    ink_cash = client.post("/api/finance/cash", headers=H(SOHIB), json={"name": "Касса-инк", "business_id": "zastroyshchik", "responsible_user_id": ids[CASHIER]}).json()
    client.post("/api/finance/movements", headers=H(CASHIER), json={"cash_id": ink_cash["id"], "kind": "income", "amount": 20000, "article": "Нал"})
    start = client.post("/api/inkassaciya/start", headers=H(CASHIER), json={"cash_id": ink_cash["id"], "shift_ref": "смена-1"})
    check("inkassaciya start 201, calc=20000", start.status_code == 201 and start.json()["calc_amount"] in ("20000.00", "20000"), start.text)
    ink_id = start.json()["id"]
    fact = client.post(f"/api/inkassaciya/{ink_id}/fact", headers=H(CASHIER), json={"fact_amount": 19500})
    check("fact -> in_transit + discrepancy -500", fact.status_code == 200 and fact.json()["status"] == "in_transit" and fact.json()["discrepancy"] in ("-500.00", "-500"), fact.text)
    bal_ink = client.get(f"/api/finance/cash/{ink_cash['id']}/balance", headers=H(CASHIER)).json()
    check("cash emptied after collection (0)", bal_ink["balance"] in ("0.00", "0"), str(bal_ink))
    # Тот же кассир не может подтвердить
    same = client.post(f"/api/inkassaciya/{ink_id}/accept", headers=H(CASHIER), json={"accepted_amount": 19500})
    check("same-user accept blocked (403 or 409)", same.status_code in (403, 409), same.text)
    # Получатель подтверждает
    acc = client.post(f"/api/inkassaciya/{ink_id}/accept", headers=H(RECEIVER), json={"accepted_amount": 19500})
    check("receiver accept -> accepted", acc.status_code == 200 and acc.json()["status"] == "accepted", acc.text)

    print("\n=== 7. Снабжение + согласование троих (§8.2, §9.5) ===")
    req = client.post("/api/supply/requests", headers=H(SUPPLY), json={"business_id": "beton", "items": [{"name": "Цемент", "qty": 10}]})
    check("supply request 201", req.status_code == 201, req.text)
    small = client.post("/api/supply/purchases", headers=H(SUPPLY), json={"business_id": "beton", "amount": 10000})
    check("small purchase auto-approved", small.status_code == 201 and small.json()["status"] == "approved", small.text)
    big = client.post("/api/supply/purchases", headers=H(SUPPLY), json={"business_id": "beton", "amount": 90000})
    check("big purchase pending_approval + approval created", big.status_code == 201 and big.json()["status"] == "pending_approval" and big.json()["approval"], big.text)
    ap_id = big.json()["approval"]["id"]
    # Не-владелец не может голосовать
    nv = client.post(f"/api/owners/approvals/{ap_id}/vote", headers=H(SUPPLY), json={"decision": "yes"})
    check("non-owner vote blocked (403)", nv.status_code == 403, nv.text)
    # Все трое голосуют yes
    client.post(f"/api/owners/approvals/{ap_id}/vote", headers=H(SOHIB), json={"decision": "yes"})
    client.post(f"/api/owners/approvals/{ap_id}/vote", headers=H(IFTIKHOR), json={"decision": "yes"})
    fin = client.post(f"/api/owners/approvals/{ap_id}/vote", headers=H(DOVUD), json={"decision": "yes"})
    check("all three yes -> approved", fin.json()["result"] == "approved", fin.text)

    print("\n=== 8. Защита владельцев (§8.2) ===")
    dis = client.post("/api/owners/access", headers=H(SOHIB), json={"user_id": ids[DOVUD], "resource": "order", "action": "view", "scope": "all", "active": False})
    check("disable owner access -> pending approval (not immediate)", dis.status_code in (200, 201) and "pending_approval" in dis.json(), dis.text)
    dis_emp = client.post("/api/owners/access", headers=H(SOHIB), json={"user_id": ids[SALES], "resource": "order", "action": "view", "scope": "all", "active": False})
    check("disable normal employee access -> ok", dis_emp.status_code in (200, 201) and "pending_approval" not in dis_emp.json(), dis_emp.text)

    print("\n=== 9. Заводы: заморозка рецептуры + автосписание (§7.3, §9.3) ===")
    stock_before = {s["nomenclature_id"]: s["qty"] for s in client.get("/api/beton/stock", headers=H(OPERATOR)).json()}
    order = client.post("/api/beton/orders", headers=H(OPERATOR), json={"mark": "M300", "volume": 10, "amount": 5000, "title": "Заказ бетона"})
    check("operator creates beton order 201 (recipe frozen)", order.status_code == 201 and order.json().get("payload_frozen"), order.text)
    stock_after = {s["nomenclature_id"]: s["qty"] for s in client.get("/api/beton/stock", headers=H(OPERATOR)).json()}
    # цемент 0.35 * 10 = 3.5 списано
    decreased = any(float(stock_after[k]) < float(stock_before[k]) for k in stock_after if k in stock_before)
    check("raw stock auto-written-off by recipe", decreased, f"before={stock_before} after={stock_after}")
    # Отгрузка ≠ касса: оператор отгружает, но не имеет прав на кассу
    tkt = client.post("/api/beton/shipping", headers=H(OPERATOR), json={"order_id": order.json()["id"], "vehicle": "A123", "qty": 10})
    check("operator ships (talon) 201", tkt.status_code == 201, tkt.text)
    nocash = client.post("/api/finance/movements", headers=H(OPERATOR), json={"cash_id": beton_cash["id"], "kind": "income", "amount": 5000})
    check("operator has NO cash access (403) — отгрузка≠касса", nocash.status_code == 403, nocash.text)

    print("\n=== 10. Отдел проверки read-only (§9.8) ===")
    check("auditor reads audit log 200", client.get("/api/audit/log", headers=H(AUDITOR)).status_code == 200)
    check("auditor cash reconcile 200", client.get("/api/audit/reconcile/cash", headers=H(AUDITOR)).status_code == 200)
    act = client.post("/api/audit/acts", headers=H(AUDITOR), json={"title": "Проверка касс", "business_id": "zastroyshchik"})
    check("auditor creates act 201", act.status_code == 201, act.text)
    esc = client.post("/api/audit/escalations", headers=H(AUDITOR), json={"act_id": act.json()["id"], "reason": "нарушение", "bypass_business": "zastroyshchik"})
    check("escalation to all 3 owners", esc.status_code == 201 and set(esc.json()["to_owners"]) == {"sohib", "iftikhor", "dovud"}, esc.text)
    ac2 = client.post("/api/finance/movements", headers=H(AUDITOR), json={"cash_id": cash_id, "kind": "income", "amount": 1})
    check("auditor cannot mutate money (403, read-only)", ac2.status_code == 403, ac2.text)

    print("\n=== 11. Аналитика консолидированная (§9.7) ===")
    summ = client.get("/api/owners/analytics/summary", headers=H(SOHIB))
    check("summary has by_business + total", summ.status_code == 200 and "by_business" in summ.json() and "total" in summ.json(), summ.text)

    print("\n=== 12. Крупный расход → согласование троих (§8.2) ===")
    big_cash = client.post("/api/finance/cash", headers=H(SOHIB), json={"name": "Касса-крупн", "business_id": "beton"}).json()
    client.post("/api/finance/movements", headers=H(SOHIB), json={"cash_id": big_cash["id"], "kind": "income", "amount": 200000, "article": "Пополнение"})
    exp = client.post("/api/finance/movements", headers=H(SOHIB), json={"cash_id": big_cash["id"], "kind": "expense", "amount": 90000, "article": "Крупная закупка"})
    check("large expense blocked -> 409 approval_required", exp.status_code == 409 and exp.json()["error"]["code"] == "approval_required", exp.text)
    exp_ap = exp.json()["error"]["details"]["approval_id"]
    for who in (SOHIB, IFTIKHOR, DOVUD):
        client.post(f"/api/owners/approvals/{exp_ap}/vote", headers=H(who), json={"decision": "yes"})
    exp2 = client.post("/api/finance/movements", headers=H(SOHIB), json={"cash_id": big_cash["id"], "kind": "expense", "amount": 90000, "article": "Крупная закупка", "approval_ref": exp_ap})
    check("large expense allowed after 3-owner approval", exp2.status_code == 201, exp2.text)

    print("\n=== 13. Аванс ≠ выручка в аналитике (§7.4) ===")
    proj_cash = client.post("/api/finance/cash", headers=H(SOHIB), json={"name": "Касса-аванс", "business_id": "proektnaya"}).json()
    client.post("/api/finance/movements", headers=H(SOHIB), json={"cash_id": proj_cash["id"], "kind": "income", "amount": 40000, "article": "Аванс по договору", "income_stage": "advance"})
    s2 = client.get("/api/owners/analytics/summary", headers=H(SOHIB)).json()
    proj = next((b for b in s2["by_business"] if b["business_id"] == "proektnaya"), None)
    check("advance = obligation, not revenue", proj and proj["advances"] in ("40000.00", "40000") and proj["income"] in ("0.00", "0"), str(proj))

    print("\n=== 14. Изоляция own_business на списках (§8.4) ===")
    client.post("/api/zastroyshchik/objects", headers=H(SOHIB), json={"name": "Объект-З", "business_id": "zastroyshchik"})
    client.post("/api/zastroyshchik/objects", headers=H(SOHIB), json={"name": "Объект-Б", "business_id": "beton"})
    fo = client.get("/api/zastroyshchik/objects", headers=H(FOREMAN))
    check("foreman list scoped to own business only", fo.status_code == 200 and all(o["business_id"] == "zastroyshchik" for o in fo.json()["items"]), fo.text)
    fo2 = client.get("/api/zastroyshchik/objects?business_id=beton", headers=H(FOREMAN))
    check("foreman denied foreign business explicitly (403)", fo2.status_code == 403, fo2.text)

    print("\n=== 15. Защита владельцев: реальное отключение доступа (§8.2) ===")
    dis = client.post("/api/owners/access", headers=H(SOHIB), json={"user_id": ids[DOVUD], "resource": "order", "action": "view", "scope": "all", "active": False})
    ap_dis = dis.json()["pending_approval"]["id"]
    self_vote = client.post(f"/api/owners/approvals/{ap_dis}/vote", headers=H(DOVUD), json={"decision": "yes"})
    check("target owner cannot approve own disable (403)", self_vote.status_code == 403, self_vote.text)
    client.post(f"/api/owners/approvals/{ap_dis}/vote", headers=H(IFTIKHOR), json={"decision": "yes"})
    relog = client.post("/api/auth/login", json={"phone": DOVUD, "password": "arkand"})
    check("disabled owner cannot login after another owner's consent (403)", relog.status_code == 403, relog.text)

    print(f"\n================  ИТОГО: PASS={PASS}  FAIL={FAIL}  ================")
    if FAIL:
        print("Провалы:")
        for f in FAILURES:
            print("  -", f)
        sys.exit(1)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ.")


if __name__ == "__main__":
    main()
