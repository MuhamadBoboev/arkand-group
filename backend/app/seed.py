"""Демо-данные: 3 владельца + роли/права (§8), бизнесы, справочники, кассы, рецептура, объект.

Запуск:  python -m app.seed
Пароль всех демо-пользователей: arkand
"""
from __future__ import annotations

from decimal import Decimal

from app.core.constants import Business, MoneyKind, MoneyStatus, OwnerType, StockStatus
from app.core.permissions import ROLE_DEFS, all_permission_tuples
from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine, now_utc
from app.db.models import (
    BusinessEntity,
    CashRegister,
    ConstructionObject,
    Counterparty,
    Employee,
    Estimate,
    MoneyMovement,
    Nomenclature,
    Owner,
    Permission,
    Recipe,
    Role,
    RolePermission,
    Unit,
    User,
    UserRole,
    WarehouseStock,
)

PWD = "arkand"


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("[!] Database already seeded - skipping.")
            return

        # --- Permissions ---
        perm_map: dict[tuple, str] = {}
        for (r, a, s) in all_permission_tuples():
            p = Permission(resource=r, action=a, scope=s)
            db.add(p)
            db.flush()
            perm_map[(r, a, s)] = p.id

        # --- Roles ---
        role_map: dict[str, str] = {}
        for name, d in ROLE_DEFS.items():
            role = Role(name=name, title=d["title"])
            db.add(role)
            db.flush()
            role_map[name] = role.id
            for trip in d["permissions"]:
                db.add(RolePermission(role_id=role.id, permission_id=perm_map[tuple(trip)]))

        # --- Businesses (id = константа типа, чтобы business_id был согласован везде) ---
        businesses = [
            (Business.ZASTROYSHCHIK, "Застройщик"),
            (Business.PROEKTNAYA, "Проектная компания"),
            (Business.BETON, "Бетонный завод"),
            (Business.SHCHEBEN, "Щебёночный завод"),
            (Business.SUPPLY, "Снабжение"),
            (Business.FINANCE, "Финансы"),
        ]
        for bid, nm in businesses:
            db.add(BusinessEntity(id=bid, name=nm, type=bid))
        db.flush()

        # --- Users ---
        def mk_user(full_name: str, phone: str) -> User:
            u = User(full_name=full_name, phone=phone, password_hash=hash_password(PWD), is_active=True)
            db.add(u)
            db.flush()
            return u

        sohib = mk_user("Сохиб", "+992900000001")
        iftikhor = mk_user("Ифтихор", "+992900000002")
        dovud = mk_user("Довуд", "+992900000003")
        cashier = mk_user("Кассир застройщика", "+992900000010")
        supplier_u = mk_user("Снабженец", "+992900000011")
        auditor = mk_user("Ревизор", "+992900000012")
        chief = mk_user("Главный бухгалтер", "+992900000013")
        operator = mk_user("Оператор бетонного завода", "+992900000014")
        receiver = mk_user("Директор (приём инкассации)", "+992900000015")
        sales = mk_user("Менеджер по продажам", "+992900000016")
        architect = mk_user("Архитектор", "+992900000017")
        foreman = mk_user("Прораб", "+992900000018")

        # --- Owners (§8.1) ---
        db.add(Owner(user_id=sohib.id, owner_type=OwnerType.SOHIB))
        db.add(Owner(user_id=iftikhor.id, owner_type=OwnerType.IFTIKHOR))
        db.add(Owner(user_id=dovud.id, owner_type=OwnerType.DOVUD))

        # --- Роли пользователей ---
        def assign(u: User, role_name: str) -> None:
            db.add(UserRole(user_id=u.id, role_id=role_map[role_name]))

        assign(sohib, "owner_full")
        assign(iftikhor, "owner_full")
        assign(dovud, "owner_project")
        assign(cashier, "cashier")
        assign(supplier_u, "supply_team")
        assign(auditor, "auditor")
        assign(chief, "chief_accountant")
        assign(operator, "operator")
        assign(receiver, "cash_receiver")
        assign(sales, "sales_manager")
        assign(architect, "architect")
        assign(foreman, "foreman")

        # --- Employees (привязка к бизнесу для scope own_business) ---
        def emp(u: User, business_id: str | None, position: str, salary: str | None = None) -> None:
            db.add(Employee(user_id=u.id, business_id=business_id, position=position,
                            salary=Decimal(salary) if salary else None))

        emp(dovud, Business.PROEKTNAYA, "Руководитель проектной")
        emp(cashier, Business.ZASTROYSHCHIK, "Кассир", "4000")
        emp(supplier_u, Business.SUPPLY, "Снабженец", "5000")
        emp(auditor, Business.AUDIT, "Ревизор", "6000")
        emp(chief, Business.FINANCE, "Главный бухгалтер", "9000")
        emp(operator, Business.BETON, "Оператор", "4500")
        emp(receiver, Business.FINANCE, "Директор", "12000")
        emp(sales, Business.ZASTROYSHCHIK, "Менеджер продаж", "4000")
        emp(architect, Business.PROEKTNAYA, "Архитектор", "7000")
        emp(foreman, Business.ZASTROYSHCHIK, "Прораб", "5000")
        db.flush()

        # --- Единицы и номенклатура ---
        units = {}
        for code, title in [("шт", "штука"), ("м3", "куб. метр"), ("т", "тонна"), ("кг", "килограмм"), ("л", "литр")]:
            u = Unit(code=code, title=title)
            db.add(u)
            db.flush()
            units[code] = u.id

        cement = Nomenclature(name="Цемент М400", unit_id=units["т"], category="Сырьё")
        shcheben_n = Nomenclature(name="Щебень 5-20", unit_id=units["м3"], category="Сырьё")
        sand = Nomenclature(name="Песок", unit_id=units["м3"], category="Сырьё")
        for n in (cement, shcheben_n, sand):
            db.add(n)
        db.flush()

        db.add(Counterparty(name='ООО "Стройпоставка"', type="поставщик", phone="+992900001000"))
        db.add(Counterparty(name="Ахмадов Рустам (клиент)", type="клиент", phone="+992900002000"))

        # --- Кассы ---
        cash_z = CashRegister(name="Касса застройщика", business_id=Business.ZASTROYSHCHIK,
                              limit_amount=Decimal("100000"), responsible_user_id=cashier.id)
        cash_b = CashRegister(name="Касса бетонного завода", business_id=Business.BETON,
                              limit_amount=Decimal("150000"))
        cash_p = CashRegister(name="Касса проектной", business_id=Business.PROEKTNAYA)
        for c in (cash_z, cash_b, cash_p):
            db.add(c)
        db.flush()

        # --- Рецептура бетона (замораживается в заказ §7.3) ---
        db.add(Recipe(business_id=Business.BETON, mark="M300", frozen_json={
            "components": [
                {"nomenclature_id": cement.id, "qty": 0.35},
                {"nomenclature_id": shcheben_n.id, "qty": 0.8},
                {"nomenclature_id": sand.id, "qty": 0.5},
            ]
        }))

        # --- Начальный остаток сырья на бетонном заводе (для автосписания) ---
        for nid, qty in [(cement.id, "1000"), (shcheben_n.id, "1000"), (sand.id, "1000")]:
            db.add(WarehouseStock(business_id=Business.BETON, nomenclature_id=nid,
                                  qty=Decimal(qty), status=StockStatus.ON_STOCK))

        # --- Объект застройщика + смета ---
        obj = ConstructionObject(business_id=Business.ZASTROYSHCHIK, name="ЖК «Арканд-1»",
                                 address="г. Душанбе, пр. Рудаки 1", city="Душанбе")
        db.add(obj)
        db.flush()
        db.add(Estimate(object_id=obj.id, plan_amount=Decimal("1000000"), fact_amount=Decimal("250000"),
                        plan_json={"работы": "фундамент, каркас"}))

        # --- Пара движений по кассе застройщика (для аналитики/дашборда) ---
        db.add(MoneyMovement(cash_id=cash_z.id, business_id=Business.ZASTROYSHCHIK, kind=MoneyKind.INCOME,
                             status=MoneyStatus.IN_CASH, amount=Decimal("50000"), article="Аванс по договору",
                             created_by=cashier.id))
        db.add(MoneyMovement(cash_id=cash_z.id, business_id=Business.ZASTROYSHCHIK, kind=MoneyKind.EXPENSE,
                             status=MoneyStatus.IN_CASH, amount=Decimal("12000"), article="Закупка материалов",
                             created_by=cashier.id))

        db.commit()
        print("[OK] Demo data created.")
        print("  Owners:  +992900000001 (Sohib), +992900000002 (Iftikhor), +992900000003 (Dovud)")
        print("  Others:  ...010 cashier, ...011 supply, ...012 auditor, ...013 chief_acc,")
        print("           ...014 operator, ...015 receiver, ...016 sales, ...017 architect")
        print("  Password for all: arkand")
    finally:
        db.close()


# (phone, ФИО, role_name, owner_type, business_id, salary) — для идемпотентной дозаливки
_DEMO_USERS = [
    ("+992900000001", "Сохиб", "owner_full", OwnerType.SOHIB, None, None),
    ("+992900000002", "Ифтихор", "owner_full", OwnerType.IFTIKHOR, None, None),
    ("+992900000003", "Довуд", "owner_project", OwnerType.DOVUD, Business.PROEKTNAYA, None),
    ("+992900000010", "Кассир застройщика", "cashier", None, Business.ZASTROYSHCHIK, "4000"),
    ("+992900000011", "Снабженец", "supply_team", None, Business.SUPPLY, "5000"),
    ("+992900000012", "Ревизор", "auditor", None, Business.AUDIT, "6000"),
    ("+992900000013", "Главный бухгалтер", "chief_accountant", None, Business.FINANCE, "9000"),
    ("+992900000014", "Оператор бетонного завода", "operator", None, Business.BETON, "4500"),
    ("+992900000015", "Директор (приём инкассации)", "cash_receiver", None, Business.FINANCE, "12000"),
    ("+992900000016", "Менеджер по продажам", "sales_manager", None, Business.ZASTROYSHCHIK, "4000"),
    ("+992900000017", "Архитектор", "architect", None, Business.PROEKTNAYA, "7000"),
    ("+992900000018", "Прораб", "foreman", None, Business.ZASTROYSHCHIK, "5000"),
]


def ensure_demo_users() -> None:
    """Идемпотентно дозаливает недостающих демо-пользователей (роли/бизнесы уже засеяны run())."""
    db = SessionLocal()
    try:
        created = 0
        for phone, name, role_name, owner_type, business_id, salary in _DEMO_USERS:
            if db.query(User).filter(User.phone == phone).first():
                continue
            role = db.query(Role).filter(Role.name == role_name).first()
            if role is None:
                continue
            u = User(full_name=name, phone=phone, password_hash=hash_password(PWD), is_active=True)
            db.add(u)
            db.flush()
            db.add(UserRole(user_id=u.id, role_id=role.id))
            if owner_type:
                db.add(Owner(user_id=u.id, owner_type=owner_type))
            db.add(Employee(user_id=u.id, business_id=business_id, position=name,
                            salary=Decimal(salary) if salary else None, hired_at=now_utc().date()))
            created += 1
        db.commit()
        if created:
            print(f"[OK] Ensured {created} demo user(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
    ensure_demo_users()
