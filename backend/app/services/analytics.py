"""Аналитика (§9.7): консолидация доходов/расходов/прибыли. Redis-кеш тяжёлых агрегатов (§6.1)."""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import MoneyKind
from app.db.models import BusinessEntity, MoneyMovement

_CACHE_TTL = 30  # сек — деньги коротко (§6.1)
_sync_redis = None


def _redis():
    global _sync_redis
    if settings.redis_url and _sync_redis is None:
        try:
            import redis

            _sync_redis = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            _sync_redis = None
    return _sync_redis


def _compute_summary(db: Session, period: str | None) -> dict:
    # Группируем по бизнесу, типу и стадии дохода, чтобы отделить авансы от выручки (§7.4)
    q = db.query(
        MoneyMovement.business_id,
        MoneyMovement.kind,
        MoneyMovement.income_stage,
        func.coalesce(func.sum(MoneyMovement.amount), 0),
    )
    if period:
        q = q.filter(func.strftime("%Y-%m", MoneyMovement.created_at) == period) if settings.is_sqlite else \
            q.filter(func.to_char(MoneyMovement.created_at, "YYYY-MM") == period)
    q = q.group_by(MoneyMovement.business_id, MoneyMovement.kind, MoneyMovement.income_stage)

    by_business: dict[str, dict] = {}
    for business_id, kind, stage, total in q.all():
        b = by_business.setdefault(business_id, {"income": Decimal(0), "expense": Decimal(0), "advances": Decimal(0)})
        amt = Decimal(total)
        if kind == "expense":
            b["expense"] += amt
        elif stage == "advance":
            # Аванс = обязательство, НЕ выручка (§7.4) — не идёт в доход/прибыль
            b["advances"] += amt
        else:
            b["income"] += amt

    names = {b.id: b.name for b in db.query(BusinessEntity).all()}
    rows = []
    total_income = Decimal(0)
    total_expense = Decimal(0)
    total_advances = Decimal(0)
    for bid, vals in by_business.items():
        income = vals["income"]
        expense = vals["expense"]
        advances = vals["advances"]
        total_income += income
        total_expense += expense
        total_advances += advances
        rows.append({
            "business_id": bid,
            "business_name": names.get(bid, bid),
            "income": str(income),
            "expense": str(expense),
            "advances": str(advances),  # обязательства, не выручка
            "profit": str(income - expense),
        })

    return {
        "period": period,
        "by_business": rows,
        "total": {
            "income": str(total_income),
            "expense": str(total_expense),
            "advances": str(total_advances),
            "profit": str(total_income - total_expense),
        },
    }


def summary(db: Session, period: str | None = None) -> dict:
    """Сводная по холдингу. Читает из Redis-кеша, если доступен (§6.1)."""
    r = _redis()
    key = f"analytics:summary:{period or 'all'}"
    if r:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    data = _compute_summary(db, period)

    if r:
        try:
            r.setex(key, _CACHE_TTL, json.dumps(data))
        except Exception:
            pass
    return data


def invalidate_summary() -> None:
    r = _redis()
    if r:
        try:
            for k in r.scan_iter("analytics:summary:*"):
                r.delete(k)
        except Exception:
            pass
