"""Демо-данные: 3 владельца + роли/права (§8), бизнесы, справочники, кассы, рецептура, объект.

Запуск:  python -m app.seed
Пароль всех демо-пользователей: arkand
"""
from __future__ import annotations

from decimal import Decimal

from app.core.constants import (
    Business,
    DebtStatus,
    IncomeStage,
    MoneyKind,
    MoneyStatus,
    OrderStatus,
    OwnerType,
    StockStatus,
)
from app.core.permissions import ROLE_DEFS, all_permission_tuples
from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine, now_utc
from app.db.models import (
    BusinessEntity,
    CalendarEvent,
    CapacityRecord,
    CashRegister,
    Client,
    ConstructionObject,
    Contract,
    Counterparty,
    Debt,
    Employee,
    Estimate,
    Fraction,
    FractionOutput,
    FuelConsumption,
    InspectionAct,
    InspectionPlan,
    Limit,
    MoneyMovement,
    Nomenclature,
    Order,
    Owner,
    Permission,
    ProductionShift,
    Project,
    Purchase,
    QualityPass,
    Receipt,
    Recipe,
    Remark,
    Role,
    RolePermission,
    Salary,
    Stage,
    Supplier,
    SupervisionObject,
    SupervisionPayment,
    SupplyRequest,
    Task,
    Unit,
    User,
    UserRole,
    Vehicle,
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


def ensure_demo_data() -> None:
    """Идемпотентно насыщает демо-данными КАЖДУЮ систему (добавляет только пустые категории)."""
    db = SessionLocal()
    try:
        def uid(phone: str) -> str | None:
            u = db.query(User).filter(User.phone == phone).first()
            return u.id if u else None

        def cash_of(business_id: str) -> CashRegister | None:
            return db.query(CashRegister).filter(CashRegister.business_id == business_id).first()

        def nom(name: str) -> str | None:
            n = db.query(Nomenclature).filter(Nomenclature.name == name).first()
            return n.id if n else None

        sohib = uid("+992900000001")
        cashier = uid("+992900000010")
        operator = uid("+992900000014")
        supplier_u = uid("+992900000011")
        architect = uid("+992900000017")
        foreman = uid("+992900000018")
        auditor = uid("+992900000012")
        chief = uid("+992900000013")

        # Кассы для всех бизнесов (для аналитики по каждому)
        biz_cash = {}
        for bid, nm in [(Business.ZASTROYSHCHIK, "Касса застройщика"), (Business.PROEKTNAYA, "Касса проектной"),
                        (Business.BETON, "Касса бетонного завода"), (Business.SHCHEBEN, "Касса щебёночного завода"),
                        (Business.SUPPLY, "Касса снабжения"), (Business.FINANCE, "Главная касса")]:
            c = cash_of(bid)
            if c is None:
                c = CashRegister(name=nm, business_id=bid, created_by=sohib)
                db.add(c)
                db.flush()
            biz_cash[bid] = c

        # ---------- ФИНАНСЫ: движения по всем бизнесам (для дашборда) ----------
        if db.query(MoneyMovement).filter(MoneyMovement.article == "Оплата за бетон").count() == 0:
            demo_mv = [
                (Business.BETON, MoneyKind.INCOME, "120000", "Оплата за бетон", IncomeStage.REVENUE),
                (Business.BETON, MoneyKind.EXPENSE, "45000", "Закупка цемента", None),
                (Business.SHCHEBEN, MoneyKind.INCOME, "80000", "Оплата за щебень", IncomeStage.REVENUE),
                (Business.SHCHEBEN, MoneyKind.EXPENSE, "30000", "Солярка и электроэнергия", None),
                (Business.PROEKTNAYA, MoneyKind.INCOME, "60000", "Аванс по договору", IncomeStage.ADVANCE),
                (Business.PROEKTNAYA, MoneyKind.INCOME, "40000", "Оплата за проект", IncomeStage.REVENUE),
                (Business.PROEKTNAYA, MoneyKind.EXPENSE, "15000", "Зарплата проектировщиков", None),
                (Business.ZASTROYSHCHIK, MoneyKind.INCOME, "200000", "Продажа квартиры", IncomeStage.REVENUE),
            ]
            for bid, kind, amt, art, stage in demo_mv:
                db.add(MoneyMovement(cash_id=biz_cash[bid].id, business_id=bid, kind=kind, status=MoneyStatus.IN_CASH,
                                     income_stage=stage, amount=Decimal(amt), article=art, created_by=sohib))

        # ---------- ФИНАНСЫ: зарплаты и долги ----------
        if db.query(Salary).count() == 0:
            for emp in db.query(Employee).limit(4).all():
                db.add(Salary(employee_id=emp.id, period="2026-06", accrued=emp.salary or Decimal("4000"),
                              paid=Decimal("0"), created_by=chief))
        if db.query(Debt).count() == 0:
            db.add(Debt(from_business=Business.BETON, to_business=Business.SHCHEBEN, amount=Decimal("25000"),
                        status=DebtStatus.OPEN, basis_ref="Передача щебня", created_by=chief))
            db.add(Debt(from_business=Business.ZASTROYSHCHIK, to_business=Business.SUPPLY, amount=Decimal("18000"),
                        status=DebtStatus.PARTIAL, paid_amount=Decimal("8000"), created_by=chief))

        # ---------- ЗАСТРОЙЩИК: объекты ----------
        if db.query(ConstructionObject).count() <= 1:
            for nm, addr, city in [("ЖК «Арканд-2»", "ул. Айни 45", "Душанбе"),
                                   ("ТЦ «Пойтахт»", "пр. Сомони 12", "Душанбе"),
                                   ("Коттеджный посёлок «Сад»", "с. Гиссар", "Гиссар")]:
                o = ConstructionObject(business_id=Business.ZASTROYSHCHIK, name=nm, address=addr, city=city, created_by=foreman)
                db.add(o)
                db.flush()
                db.add(Estimate(object_id=o.id, plan_amount=Decimal("1500000"), fact_amount=Decimal("420000"),
                                plan_json={"работы": "фундамент, каркас, отделка"}, created_by=foreman))

        # ---------- ПРОЕКТНАЯ: клиенты, договоры, проекты, надзор ----------
        if db.query(Client).count() == 0:
            clients = []
            for fn, ph in [("Рахимов Далер", "+992900010001"), ("Собирова Нигина", "+992900010002"),
                           ("ООО «СтройИнвест»", "+992900010003")]:
                cl = Client(full_name=fn, phone=ph, registered=True, created_by=architect)
                db.add(cl)
                db.flush()
                clients.append(cl)
            for cl, amount in zip(clients, ["350000", "780000", "1200000"]):
                db.add(Contract(client_id=cl.id, amount=Decimal(amount), status="active",
                                schedule_json={"advance": 50, "mid": 30, "final": 20}, created_by=architect))
            for title in ["Индивидуальный жилой дом", "Офисное здание", "Реконструкция цеха"]:
                p = Project(title=title, status="active", created_by=architect)
                db.add(p)
                db.flush()
                for i, stg in enumerate(["Генплан", "Эскиз", "Конструктив", "Сдача"]):
                    db.add(Stage(project_id=p.id, name=stg, order_index=i,
                                 status="done" if i == 0 else "pending", created_by=architect))
            for nm, fee in [("Надзор: ЖК «Восток»", "3000"), ("Надзор: Школа №25", "2500")]:
                so = SupervisionObject(name=nm, manager_user_id=architect, monthly_fee=Decimal(fee), created_by=architect)
                db.add(so)
                db.flush()
                db.add(SupervisionPayment(supervision_object_id=so.id, period="2026-06", amount=Decimal(fee), collected_by=architect, created_by=architect))

        # ---------- БЕТОННЫЙ ЗАВОД: рецептуры, заказы, качество, техника ----------
        if db.query(Recipe).filter(Recipe.business_id == Business.BETON).count() <= 1:
            for mark in ["M200", "M400"]:
                db.add(Recipe(business_id=Business.BETON, mark=mark, frozen_json={"components": [
                    {"nomenclature_id": nom("Цемент М400"), "qty": 0.32},
                    {"nomenclature_id": nom("Щебень 5-20"), "qty": 0.85},
                    {"nomenclature_id": nom("Песок"), "qty": 0.55},
                ]}, created_by=operator))
        if db.query(Order).filter(Order.business_id == Business.BETON).count() == 0:
            for mark, vol, amt, st in [("M300", 12, 42000, OrderStatus.SHIPPED), ("M200", 8, 24000, OrderStatus.NEW),
                                       ("M400", 20, 90000, OrderStatus.IN_PRODUCTION)]:
                db.add(Order(business_id=Business.BETON, mark=mark, volume=Decimal(vol), amount=Decimal(amt),
                             status=st, payment_status="оплачено", created_by=operator))
        if db.query(QualityPass).count() == 0:
            db.add(QualityPass(business_id=Business.BETON, sample_ref="Партия №128", test_day=7, result="28.4 МПа", passed=True, created_by=operator))
            db.add(QualityPass(business_id=Business.BETON, sample_ref="Партия №128", test_day=28, result="М300 соответствует", passed=True, created_by=operator))
        if db.query(Vehicle).filter(Vehicle.business_id == Business.BETON).count() == 0:
            db.add(Vehicle(business_id=Business.BETON, name="Миксер №1", kind="миксер", plate="0101 AA", created_by=operator))
            db.add(Vehicle(business_id=Business.BETON, name="Миксер №2", kind="миксер", plate="0102 AA", created_by=operator))

        # ---------- ЩЕБЁНОЧНЫЙ ЗАВОД: фракции, смены, выпуск, солярка, мощность, заказы ----------
        if db.query(Fraction).count() == 0:
            fr_ids = {}
            for nm in ["Песок", "Щебень 5-20", "Щебень 20-40", "Отсев", "Пудра"]:
                f = Fraction(business_id=Business.SHCHEBEN, name=nm, created_by=operator)
                db.add(f)
                db.flush()
                fr_ids[nm] = f.id
            shift = ProductionShift(business_id=Business.SHCHEBEN, note="Дневная смена", created_by=operator)
            db.add(shift)
            db.flush()
            for nm, qty in [("Щебень 5-20", 120), ("Щебень 20-40", 90), ("Песок", 60)]:
                db.add(FractionOutput(shift_id=shift.id, fraction_id=fr_ids[nm], qty=Decimal(qty), created_by=operator))
            db.add(FuelConsumption(business_id=Business.SHCHEBEN, liters=Decimal("180"), norm_liters=Decimal("170"), created_by=operator))
            db.add(CapacityRecord(business_id=Business.SHCHEBEN, period="2026-06", output_qty=Decimal("2700"), cost_per_unit=Decimal("42.50"), created_by=operator))
            for mark, vol, amt in [("Щебень 5-20", 30, 21000), ("Песок", 25, 12500)]:
                db.add(Order(business_id=Business.SHCHEBEN, mark=mark, volume=Decimal(vol), amount=Decimal(amt), status=OrderStatus.NEW, created_by=operator))

        # ---------- СНАБЖЕНИЕ: поставщики, заявки, закупки, лимиты, оприходование ----------
        if db.query(SupplyRequest).count() == 0:
            cp = db.query(Counterparty).filter(Counterparty.type == "поставщик").first()
            if cp:
                db.add(Supplier(counterparty_id=cp.id, rating=5, note="Надёжный поставщик", created_by=supplier_u))
            db.add(Limit(business_id=None, amount=Decimal("50000"), resource="purchase", set_by=sohib, created_by=sohib))
            for bid, items in [(Business.BETON, [{"name": "Цемент М400", "qty": 20}]),
                               (Business.ZASTROYSHCHIK, [{"name": "Кирпич", "qty": 5000}]),
                               (Business.SHCHEBEN, [{"name": "Запчасти дробилки", "qty": 3}])]:
                db.add(SupplyRequest(business_id=bid, items_json=items, status="new", created_by=supplier_u))
            db.add(Purchase(business_id=Business.BETON, amount=Decimal("35000"), status="approved", limit_ok=True, created_by=supplier_u))
            db.add(Purchase(business_id=Business.ZASTROYSHCHIK, amount=Decimal("90000"), status="pending_approval", limit_ok=False, created_by=supplier_u))
            cement_id = nom("Цемент М400")
            if cement_id:
                db.add(Receipt(business_id=Business.BETON, nomenclature_id=cement_id, qty=Decimal("20"), created_by=supplier_u))

        # ---------- ВЛАДЕЛЬЦЫ: задачи, календарь ----------
        if db.query(Task).count() == 0:
            for at, title in [(operator, "Подготовить отчёт по выпуску бетона"),
                              (supplier_u, "Согласовать цену на цемент"),
                              (foreman, "Проверить готовность фундамента ЖК-2"),
                              (chief, "Закрыть период за июнь")]:
                db.add(Task(assigned_to=at, assigned_by=sohib, title=title, status="open", created_by=sohib))
        if db.query(CalendarEvent).count() == 0:
            for t, title in [("встреча", "Совещание владельцев"), ("дедлайн", "Сдача проекта «Офис»"), ("встреча", "Приёмка бетона на объекте")]:
                db.add(CalendarEvent(type=t, title=title, owner_scope="holding", created_by=sohib))

        # ---------- ОТДЕЛ ПРОВЕРКИ: планы, акты, замечания ----------
        if db.query(InspectionAct).count() == 0:
            db.add(InspectionPlan(title="Плановая проверка касс за июнь", planned=True, created_by=auditor))
            db.add(InspectionPlan(title="Внеплановая проверка склада бетона", planned=False, created_by=auditor))
            act = InspectionAct(title="Сверка кассы застройщика", business_id=Business.ZASTROYSHCHIK, status="open",
                                summary="Расхождений не выявлено", created_by=auditor)
            db.add(act)
            db.flush()
            db.add(Remark(act_id=act.id, text="Рекомендуется чаще проводить инкассацию", status="open", created_by=auditor))

        db.commit()
        print("[OK] Demo data ensured for all systems.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
    ensure_demo_users()
    ensure_demo_data()
