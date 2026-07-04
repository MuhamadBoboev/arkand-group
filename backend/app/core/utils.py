"""Утилиты сериализации для JSON-полей и аудита."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect as sa_inspect


def jsonable(value: Any) -> Any:
    """Рекурсивно приводит значение к JSON-совместимому виду."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def model_to_dict(instance: Any) -> dict:
    """Плоский dict колонок ORM-объекта (для before/after аудита)."""
    if instance is None:
        return {}
    mapper = sa_inspect(instance).mapper
    return {col.key: jsonable(getattr(instance, col.key)) for col in mapper.column_attrs}
