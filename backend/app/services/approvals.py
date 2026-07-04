"""Согласование крупного — цифровое «добро/нет» от всех троих (§8.2)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import ApprovalResult, Decision, OwnerType
from app.core.errors import conflict, forbidden, not_found
from app.db.models import Approval
from app.realtime import channels
from app.realtime.publisher import publish
from app.services.audit import write_audit
from app.services.rbac import Principal


def create_approval(db: Session, *, kind: str, ref_id: str | None, amount: Decimal | None, note: str | None = None, actor_id: str | None = None) -> Approval:
    ap = Approval(kind=kind, ref_id=ref_id, amount=amount, result=ApprovalResult.PENDING, note=note, created_by=actor_id)
    db.add(ap)
    db.flush()
    publish(channels.OWNERS, "approval.requested", {"id": ap.id, "kind": kind, "amount": str(amount) if amount else None})
    return ap


_FIELD = {OwnerType.SOHIB: "sohib", OwnerType.IFTIKHOR: "iftikhor", OwnerType.DOVUD: "dovud"}


def vote(db: Session, *, actor: Principal, approval_id: str, decision: str) -> Approval:
    """Голос владельца. Нужны все трое (§8.2). Любой 'no' → rejected; все 'yes' → approved."""
    if not actor.is_owner or actor.owner_type not in _FIELD:
        raise forbidden("Голосовать могут только владельцы (Сохиб, Ифтихор, Довуд)")
    if decision not in (Decision.YES, Decision.NO):
        raise conflict("bad_decision", "decision: yes | no")

    ap = db.query(Approval).filter(Approval.id == approval_id).first()
    if ap is None:
        raise not_found("Согласование не найдено")
    if ap.result != ApprovalResult.PENDING:
        raise conflict("closed", "Согласование уже завершено")

    setattr(ap, _FIELD[actor.owner_type], decision)

    votes = [ap.sohib, ap.iftikhor, ap.dovud]
    if Decision.NO in votes:
        ap.result = ApprovalResult.REJECTED
    elif all(v == Decision.YES for v in votes):
        ap.result = ApprovalResult.APPROVED
    else:
        ap.result = ApprovalResult.PENDING

    db.add(ap)
    db.flush()
    write_audit(db, user_id=actor.id, action="approve", resource="approval", ref_id=ap.id,
                after={"owner": actor.owner_type, "decision": decision, "result": ap.result})
    db.commit()
    db.refresh(ap)
    publish(channels.OWNERS, "approval.voted", {"id": ap.id, "result": ap.result})
    return ap
