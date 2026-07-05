"""Серверная валидация payload для generic-эндпоинтов (§14 — валидация всего ввода).

Приводит числовые поля к нужному типу и отвергает нечисловой ввод («буквы вместо цифр»),
проверяет обязательные (NOT NULL без default) колонки.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import Integer, Numeric

from app.core.errors import bad_request


def coerce_and_validate(model, data: dict[str, Any], *, require_columns: bool = False) -> dict[str, Any]:
    columns = {c.key: c for c in model.__table__.columns}
    out: dict[str, Any] = {}

    for key, value in data.items():
        col = columns.get(key)
        if col is None:
            continue  # неизвестные поля отбрасываем
        if value is None:
            out[key] = None
            continue

        coltype = col.type
        if isinstance(coltype, Numeric):
            try:
                out[key] = Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                raise bad_request("invalid_number", f"Поле «{key}»: ожидается число")
        elif isinstance(coltype, Integer):
            try:
                out[key] = int(value)
            except (ValueError, TypeError):
                raise bad_request("invalid_integer", f"Поле «{key}»: ожидается целое число")
        else:
            out[key] = value

    if require_columns:
        for key, col in columns.items():
            if key in ("id", "created_at", "created_by"):
                continue
            if not col.nullable and col.default is None and col.server_default is None:
                if out.get(key) in (None, ""):
                    raise bad_request("required_field", f"Поле «{key}» обязательно")

    return out
