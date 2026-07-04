# ARKAND · Финансовая CRM холдинга

Единая CRM-экосистема строительного холдинга **ARKAND** — 8 подсистем на одной базе данных.
Данные вводятся один раз и мгновенно переиспользуются всеми ролями через WebSocket.

> Бренд: **ARKAND** · webrand.tj · +992 988 64 55 43 · Язык интерфейса и данных — **русский**.

Реализовано строго по ТЗ ([`docs/ARKAND_CRM_ТЗ.md`](docs/ARKAND_CRM_ТЗ.md)).

---

## Архитектура (монорепо)

```
/frontend   React + TypeScript + Vite  →  Vercel   (строгий Feature-Sliced Design)
/backend    Python + FastAPI           →  Railway  (append-only ledger, RBAC, WS)
/docs       Техническое задание (источник правды)
```

| Слой | Технология |
|------|-----------|
| Frontend | React + TS, Vite, TanStack Query v5, Zustand, TailwindCSS + CSS-токены, React Router (lazy), react-hook-form + zod, нативный WebSocket + reconnect |
| Backend | Python + FastAPI, SQLAlchemy + Alembic, Pydantic v2, JWT (access+refresh), argon2 |
| Realtime | FastAPI WebSocket + Redis Pub/Sub (с in-process fallback для локали) |
| БД | PostgreSQL (Railway) · SQLite для локальной разработки/тестов |

## 8 подсистем

1. **Застройщик** — объекты, сметы, склад, приёмка, прибыль по объекту.
2. **Проектная компания** — проектирование + авторский надзор.
3. **Бетонный завод** — товарный бетон, рецептуры, отгрузка, качество.
4. **Щебёночный завод** — фракции, добыча, дробление, себестоимость.
5. **Снабжение** — централизованные закупки, лимиты, согласование троих.
6. **Финансы** — кассы, проводки, инкассация, долги, зарплата, закрытие периода.
7. **Надстройка владельцев** — согласования, сотрудники, аналитика, календарь.
8. **Отдел проверки** — независимый аудит (только чтение).

## Сквозные правила (фундамент, §7 ТЗ)

- **Append-only** — проведённое не меняется/не удаляется, только **сторно**.
- **Заморозка значений** на дату (цена/смета/рецептура/курс).
- **Статусы у денег и товара** (`в_кассе → в_пути → принято` и т.д.).
- **Единые справочники** — контрагенты/номенклатура/единицы.
- **Разделение полномочий** — кто отгрузил ≠ кто принял деньги.
- **Неизменяемый audit_log** — кто/что/когда/до/после.

---

## Быстрый старт (локально)

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |  *nix: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # по умолчанию SQLite, Redis не обязателен
python -m app.seed            # демо-данные: 3 владельца + роли + бизнесы
uvicorn app.main:app --reload --port 8000
# Swagger:   http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_URL=http://localhost:8000
npm run dev                   # http://localhost:5173
```

## Демо-логины (после `seed`)

| Кто | Телефон (логин) | Пароль | Роль |
|-----|-----------------|--------|------|
| Сохиб | +992900000001 | arkand | Главный финансист (полный) |
| Ифтихор | +992900000002 | arkand | Суперадмин (полный) |
| Довуд | +992900000003 | arkand | Проектная компания |
| Кассир (застройщик) | +992900000010 | arkand | Кассир своей кассы |
| Снабженец | +992900000011 | arkand | Снабжение |
| Ревизор | +992900000012 | arkand | Отдел проверки (read-only) |

## Продакшн

- **Frontend → Vercel**: `VITE_API_URL` = URL бэкенда на Railway.
- **Backend → Railway**: `DATABASE_URL` (Postgres), `REDIS_URL`, `JWT_SECRET` — только через env, секреты не в коде.

---

_ARKAND · webrand.tj · +992 988 64 55 43 — единая CRM-экосистема холдинга._
