"""Generic CRUD-фабрика для сущностей модулей: list/create/get с RBAC + аудит + WS.

Append-only соблюдается: обновление/удаление проведённых сущностей не предоставляется,
где это требуется — используются доменные reverse-эндпоинты.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize
from app.core.constants import Action
from app.core.deps import get_principal
from app.core.errors import forbidden, not_found
from app.core.validation import coerce_and_validate
from app.db.base import get_db
from app.realtime import channels
from app.realtime.publisher import publish
from app.services.audit import write_audit
from app.services.rbac import Principal


def make_crud_router(*, model, resource: str, tags: list[str], business_scoped: bool = True) -> APIRouter:
    r = APIRouter(tags=tags)
    columns = {c.key for c in model.__table__.columns}
    writable = columns - {"id", "created_at"}

    @r.get("")
    def _list(
        business_id: str | None = Query(default=None),
        page: int = 1,
        size: int = 50,
        principal: Principal = Depends(get_principal),
        db: Session = Depends(get_db),
    ):
        principal.require(resource, Action.VIEW, business_id=business_id)
        q = db.query(model)

        if business_scoped and "business_id" in columns:
            scopes = principal._matching_scopes(resource, Action.VIEW)
            broad = principal.is_owner or ("all" in scopes) or ("read_only" in scopes)
            if not broad:
                # scope own_business: не даём видеть чужие бизнесы даже без фильтра (§8.4)
                allowed = list(principal.businesses) or ["__none__"]
                if business_id:
                    if business_id not in principal.businesses:
                        raise forbidden("Нет доступа к этому бизнесу")
                    q = q.filter(model.business_id == business_id)
                else:
                    q = q.filter(model.business_id.in_(allowed))
            elif business_id:
                q = q.filter(model.business_id == business_id)

        order_col = model.created_at if "created_at" in columns else model.id
        return paginate(q.order_by(order_col.desc()), page, size)

    @r.post("", status_code=201)
    def _create(payload: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        business_id = payload.get("business_id") if business_scoped else None
        principal.require(resource, Action.CREATE, business_id=business_id)
        # Валидация типов (числовые поля не принимают буквы) — §14
        data = coerce_and_validate(model, {k: v for k, v in payload.items() if k in writable})
        if "created_by" in columns:
            data["created_by"] = principal.id
        obj = model(**data)
        db.add(obj)
        db.flush()
        write_audit(db, user_id=principal.id, action="create", resource=resource, ref_id=obj.id, after=serialize(obj))
        db.commit()
        db.refresh(obj)
        if business_scoped and getattr(obj, "business_id", None):
            publish(channels.business(obj.business_id), f"{resource}.created", {"id": obj.id})
        return serialize(obj)

    @r.get("/{obj_id}")
    def _get(obj_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        obj = db.query(model).filter(model.id == obj_id).first()
        if obj is None:
            raise not_found("Не найдено")
        principal.require(resource, Action.VIEW, business_id=getattr(obj, "business_id", None))
        return serialize(obj)

    return r
