"""Отдел проверки (§9.8) — только чтение по данным систем + акты/замечания/эскалация."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize, serialize_list
from app.core.constants import Action, ActStatus, OwnerType, Resource
from app.core.deps import get_principal
from app.core.errors import not_found
from app.db.base import get_db
from app.db.models import (
    AuditLog,
    CashRegister,
    Escalation,
    Inkassaciya,
    InspectionAct,
    InspectionPlan,
    Remark,
)
from app.realtime import channels
from app.realtime.publisher import publish
from app.schemas import ActIn, EscalationIn, RemarkIn
from app.services import ledger
from app.services.audit import write_audit
from app.services.rbac import Principal

router = APIRouter(prefix="/audit", tags=["audit_dept"])


# ---------- Неизменяемый аудит-лог (read-only §7.7) ----------
@router.get("/log")
def audit_log(
    resource: str | None = Query(default=None),
    page: int = 1,
    size: int = 50,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    principal.require(Resource.AUDIT, Action.VIEW)
    q = db.query(AuditLog)
    if resource:
        q = q.filter(AuditLog.resource == resource)
    return paginate(q.order_by(AuditLog.at.desc()), page, size)


# ---------- Сверка касс: система vs факт (§9.8) ----------
@router.get("/reconcile/cash")
def reconcile_cash(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.VIEW)
    rows = []
    for c in db.query(CashRegister).all():
        system = ledger.compute_cash_balance(db, c.id)
        last_ink = (
            db.query(Inkassaciya)
            .filter(Inkassaciya.cash_id == c.id)
            .order_by(Inkassaciya.created_at.desc())
            .first()
        )
        rows.append({
            "cash_id": c.id,
            "cash_name": c.name,
            "system_balance": str(system),
            "last_inkassaciya_status": last_ink.status if last_ink else None,
            "last_discrepancy": str(last_ink.discrepancy) if last_ink and last_ink.discrepancy is not None else None,
        })
    return {"items": rows, "total": len(rows)}


# ---------- Планы проверок ----------
@router.get("/plans")
def list_plans(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.VIEW)
    return serialize_list(db.query(InspectionPlan).order_by(InspectionPlan.created_at.desc()).all())


@router.post("/plans", status_code=201)
def create_plan(title: str = Query(...), planned: bool = True, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.CREATE)
    p = InspectionPlan(title=title, planned=planned, created_by=principal.id)
    db.add(p)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="audit", ref_id=p.id, after={"title": title})
    db.commit()
    db.refresh(p)
    return serialize(p)


# ---------- Акты / замечания ----------
@router.get("/acts")
def list_acts(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.VIEW)
    return paginate(db.query(InspectionAct).order_by(InspectionAct.created_at.desc()), page, size)


@router.post("/acts", status_code=201)
def create_act(data: ActIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.CREATE)
    act = InspectionAct(**data.model_dump(), status=ActStatus.OPEN, created_by=principal.id)
    db.add(act)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="audit", ref_id=act.id, after=data.model_dump())
    db.commit()
    db.refresh(act)
    publish(channels.AUDIT, "act.created", {"id": act.id, "title": act.title})
    return serialize(act)


@router.post("/acts/{act_id}/resolve")
def resolve_act(act_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.CREATE)
    act = db.query(InspectionAct).filter(InspectionAct.id == act_id).first()
    if act is None:
        raise not_found("Акт не найден")
    act.status = ActStatus.RESOLVED
    write_audit(db, user_id=principal.id, action="update_via_reversal", resource="audit", ref_id=act.id, after={"status": "resolved"})
    db.commit()
    publish(channels.AUDIT, "act.resolved", {"id": act.id})
    return serialize(act)


@router.post("/remarks", status_code=201)
def create_remark(data: RemarkIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.CREATE)
    r = Remark(act_id=data.act_id, text=data.text, created_by=principal.id)
    db.add(r)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="audit", ref_id=r.id, after={"act_id": data.act_id})
    db.commit()
    db.refresh(r)
    publish(channels.AUDIT, "remark.created", {"id": r.id, "act_id": r.act_id})
    return serialize(r)


# ---------- Эскалация — всем троим владельцам, минуя зону нарушителя (§9.8) ----------
@router.post("/escalations", status_code=201)
def create_escalation(data: EscalationIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.AUDIT, Action.CREATE)
    esc = Escalation(
        act_id=data.act_id, remark_id=data.remark_id, reason=data.reason,
        to_owners=[OwnerType.SOHIB, OwnerType.IFTIKHOR, OwnerType.DOVUD],  # всем троим
        bypass_business=data.bypass_business, created_by=principal.id,
    )
    db.add(esc)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="audit", ref_id=esc.id, after={"reason": data.reason})
    db.commit()
    db.refresh(esc)
    publish(channels.OWNERS, "escalation.created", {"id": esc.id, "reason": esc.reason})
    publish(channels.AUDIT, "escalation.created", {"id": esc.id})
    return serialize(esc)
