"""Общие производственные роутеры (заводы §9.3/§9.4): заказы (заморозка рецептуры,
автосписание сырья) и отгрузка (talon; отгрузка ≠ приём денег §7.6)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize
from app.core.constants import Action, OrderStatus, Resource, StockStatus
from app.core.deps import get_principal
from app.core.errors import conflict, not_found
from app.core.validation import coerce_and_validate
from app.db.base import get_db
from app.db.models import Order, Recipe, ShippingTicket, WarehouseMovement
from app.realtime import channels
from app.realtime.publisher import publish
from app.services import warehouse
from app.services.audit import write_audit
from app.services.rbac import Principal


def _freeze_recipe(db: Session, business_id: str, mark: str | None, recipe_id: str | None) -> Recipe | None:
    if recipe_id:
        return db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if mark:
        return (
            db.query(Recipe)
            .filter(Recipe.business_id == business_id, Recipe.mark == mark)
            .order_by(Recipe.valid_from.desc())
            .first()
        )
    return None


def make_orders_router(business_id: str) -> APIRouter:
    r = APIRouter(tags=["orders"])

    @r.get("")
    def _list(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        principal.require(Resource.ORDER, Action.VIEW, business_id=business_id)
        return paginate(
            db.query(Order).filter(Order.business_id == business_id).order_by(Order.created_at.desc()),
            page, size,
        )

    @r.post("", status_code=201)
    def _create(payload: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        principal.require(Resource.ORDER, Action.CREATE, business_id=business_id)
        # Валидация чисел (объём/сумма не принимают буквы) — §14
        nums = coerce_and_validate(Order, {k: payload.get(k) for k in ("volume", "amount") if payload.get(k) is not None})
        recipe = _freeze_recipe(db, business_id, payload.get("mark"), payload.get("recipe_id"))
        order = Order(
            business_id=business_id,
            counterparty_id=payload.get("counterparty_id"),
            title=payload.get("title"),
            mark=payload.get("mark"),
            volume=nums.get("volume"),
            amount=nums.get("amount"),
            payment_status=payload.get("payment_status"),
            status=OrderStatus.NEW,
            payload_frozen={"recipe": recipe.frozen_json} if recipe else payload.get("payload_frozen"),  # заморозка (§7.3)
            created_by=principal.id,
        )
        db.add(order)
        db.flush()

        # Автосписание сырья по рецептуре (§9.3): склад → в производство
        volume = Decimal(str(nums.get("volume") or 0))
        if recipe and volume > 0 and isinstance(recipe.frozen_json, dict):
            for comp in recipe.frozen_json.get("components", []):
                nid = comp.get("nomenclature_id")
                per = Decimal(str(comp.get("qty", 0)))
                if nid and per > 0:
                    warehouse.adjust(
                        db, actor_id=principal.id, business_id=business_id, nomenclature_id=nid,
                        delta_qty=-(per * volume), kind="production", basis_ref=order.id,
                        status=StockStatus.ON_STOCK,
                    )

        write_audit(db, user_id=principal.id, action="create", resource="order", ref_id=order.id, after=serialize(order))
        db.commit()
        db.refresh(order)
        publish(channels.business(business_id), "order.created", {"id": order.id, "status": order.status})
        return serialize(order)

    @r.get("/{order_id}")
    def _get(order_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        principal.require(Resource.ORDER, Action.VIEW, business_id=business_id)
        o = db.query(Order).filter(Order.id == order_id).first()
        if o is None:
            raise not_found("Заказ не найден")
        return serialize(o)

    @r.post("/{order_id}/reverse", status_code=201)
    def _reverse(order_id: str, payload: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        principal.require(Resource.ORDER, Action.UPDATE_VIA_REVERSAL, business_id=business_id)
        orig = db.query(Order).filter(Order.id == order_id).first()
        if orig is None:
            raise not_found("Заказ не найден")
        if orig.reversed:
            raise conflict("already_reversed", "Заказ уже сторнирован")
        rev = Order(
            business_id=orig.business_id, counterparty_id=orig.counterparty_id,
            title=f"СТОРНО: {orig.title or ''}".strip(), mark=orig.mark, volume=orig.volume,
            amount=orig.amount, status=OrderStatus.CANCELLED, is_reversal=True, reversal_of=orig.id,
            payload_frozen=orig.payload_frozen, created_by=principal.id,
        )
        orig.reversed = True
        db.add(rev)
        db.flush()

        # Append-only склад (§7.1): вернуть списанное по рецептуре сырьё компенсирующими движениями
        prod_moves = db.query(WarehouseMovement).filter(
            WarehouseMovement.basis_ref == orig.id, WarehouseMovement.kind == "production"
        ).all()
        for pm in prod_moves:
            warehouse.adjust(
                db, actor_id=principal.id, business_id=pm.business_id, nomenclature_id=pm.nomenclature_id,
                delta_qty=-Decimal(str(pm.qty)), kind="reversal", basis_ref=rev.id,
            )

        write_audit(db, user_id=principal.id, action="reverse", resource="order", ref_id=orig.id,
                    after={"reversal_id": rev.id, "reason": payload.get("reason")})
        db.commit()
        db.refresh(rev)
        publish(channels.business(business_id), "order.reversed", {"id": rev.id, "reversal_of": orig.id})
        return serialize(rev)

    return r


def make_shipping_router(business_id: str) -> APIRouter:
    r = APIRouter(tags=["shipping"])

    @r.get("")
    def _list(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        principal.require(Resource.SHIPPING, Action.VIEW, business_id=business_id)
        return paginate(
            db.query(ShippingTicket).filter(ShippingTicket.business_id == business_id).order_by(ShippingTicket.created_at.desc()),
            page, size,
        )

    @r.post("", status_code=201)
    def _create(payload: dict, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
        # Отгрузка ≠ приём денег: shipped_by фиксируется, роль оператора не имеет прав на кассу (§7.6)
        principal.require(Resource.SHIPPING, Action.CREATE, business_id=business_id)
        nums = coerce_and_validate(ShippingTicket, {"qty": payload.get("qty")} if payload.get("qty") is not None else {})
        ticket = ShippingTicket(
            order_id=payload.get("order_id"), business_id=business_id, vehicle=payload.get("vehicle"),
            driver_user_id=payload.get("driver_user_id"), nomenclature_id=payload.get("nomenclature_id"),
            qty=nums.get("qty"), shipped_by=principal.id, created_by=principal.id,
        )
        db.add(ticket)
        db.flush()
        write_audit(db, user_id=principal.id, action="create", resource="shipping", ref_id=ticket.id, after=serialize(ticket))
        db.commit()
        db.refresh(ticket)
        publish(channels.business(business_id), "shipping.created", {"id": ticket.id, "shipped_by": principal.id})
        return serialize(ticket)

    return r
