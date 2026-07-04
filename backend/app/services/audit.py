"""Аудит-лог (§7.7) — неизменяемый журнал значимых действий. Только вставка."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.utils import jsonable
from app.db.models import AuditLog


def write_audit(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    resource: str,
    ref_id: str | None = None,
    before: Any = None,
    after: Any = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        ref_id=ref_id,
        before_json=jsonable(before) if before is not None else None,
        after_json=jsonable(after) if after is not None else None,
    )
    db.add(entry)
    # commit выполняет вызывающий эндпоинт вместе с основной операцией
    return entry
