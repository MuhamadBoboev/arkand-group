"""Общие утилиты роутеров: сериализация и пагинация (§6.5 — пагинация везде)."""
from __future__ import annotations

from typing import Any

from app.core.utils import model_to_dict


def serialize(obj: Any) -> dict:
    return model_to_dict(obj)


def serialize_list(objs: list) -> list[dict]:
    return [model_to_dict(o) for o in objs]


def paginate(query, page: int = 1, size: int = 50) -> dict:
    page = max(1, page)
    size = max(1, min(size, 200))
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"items": serialize_list(items), "total": total, "page": page, "size": size}
