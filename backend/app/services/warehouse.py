"""Склад: движение остатков (append-only движения) + синхронизация по WS (§6.3, §9.1)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import StockStatus
from app.db.models import WarehouseMovement, WarehouseStock
from app.realtime import channels
from app.realtime.publisher import publish


def get_stock(db: Session, business_id: str, nomenclature_id: str, status: str = StockStatus.ON_STOCK) -> WarehouseStock:
    row = (
        db.query(WarehouseStock)
        .filter(
            WarehouseStock.business_id == business_id,
            WarehouseStock.nomenclature_id == nomenclature_id,
            WarehouseStock.status == status,
        )
        .first()
    )
    if row is None:
        row = WarehouseStock(business_id=business_id, nomenclature_id=nomenclature_id, status=status, qty=0)
        db.add(row)
        db.flush()
    return row


def adjust(
    db: Session,
    *,
    actor_id: str,
    business_id: str,
    nomenclature_id: str,
    delta_qty: Decimal,
    kind: str,
    basis_ref: str | None = None,
    status: str = StockStatus.ON_STOCK,
) -> WarehouseStock:
    """Изменить остаток (delta может быть отрицательным). Пишет движение + WS-событие."""
    row = get_stock(db, business_id, nomenclature_id, status)
    row.qty = Decimal(row.qty) + Decimal(delta_qty)
    mv = WarehouseMovement(
        business_id=business_id,
        nomenclature_id=nomenclature_id,
        qty=Decimal(delta_qty),
        kind=kind,
        to_status=status,
        basis_ref=basis_ref,
        created_by=actor_id,
    )
    db.add(mv)
    db.flush()
    publish(channels.business(business_id), "stock.changed", {
        "business_id": business_id, "nomenclature_id": nomenclature_id,
        "qty": str(row.qty), "status": status,
    })
    return row
