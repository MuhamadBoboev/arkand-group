"""Надстройка владельцев (§9.7): сотрудники, доступы, задачи, календарь, согласования, аналитика.

Разделы Сотрудники / Аналитика / Календарь — только Сохиб и Ифтихор (§8.3).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import paginate, serialize, serialize_list
from app.core.constants import Action, OwnerType, Resource, TaskStatus
from app.core.deps import get_principal
from app.core.errors import bad_request, forbidden, not_found
from app.db.base import get_db, now_utc
from app.db.models import (
    AccessGrant,
    Approval,
    CalendarEvent,
    Employee,
    Permission,
    Task,
    User,
)
from app.schemas import AccessIn, ApprovalCreateIn, CalendarIn, EmployeeIn, TaskIn, TaskStatusIn, VoteIn
from app.services import approvals as approvals_service
from app.services.analytics import summary as analytics_summary_service
from app.services.audit import write_audit
from app.services.rbac import Principal, get_owner

router = APIRouter(prefix="/owners", tags=["owners"])


def require_top_owner(principal: Principal) -> None:
    """Разделы Сотрудники/Аналитика/Календарь — только Сохиб и Ифтихор (§8.3)."""
    if not (principal.is_owner and principal.owner_type in (OwnerType.SOHIB, OwnerType.IFTIKHOR)):
        raise forbidden("Раздел доступен только Сохибу и Ифтихору (§8.3)")


# ================= Аналитика (консолидация) =================
@router.get("/analytics/summary")
def analytics_summary(period: str | None = Query(default=None), principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)
    return analytics_summary_service(db, period)


# ================= Сотрудники (§8.3) =================
@router.get("/employees")
def list_employees(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)
    return serialize_list(db.query(Employee).order_by(Employee.created_at.desc()).all())


@router.post("/employees", status_code=201)
def hire_employee(data: EmployeeIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)
    emp = Employee(**data.model_dump(), hired_at=now_utc().date(), created_by=principal.id)
    db.add(emp)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="employee", ref_id=emp.id, after=data.model_dump())
    db.commit()
    db.refresh(emp)
    return serialize(emp)


@router.post("/employees/{emp_id}/fire")
def fire_employee(emp_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if emp is None:
        raise not_found("Сотрудник не найден")
    emp.fired_at = now_utc().date()
    write_audit(db, user_id=principal.id, action="update_via_reversal", resource="employee", ref_id=emp.id, after={"fired_at": str(emp.fired_at)})
    db.commit()
    return serialize(emp)


@router.get("/employees/{user_id}/access")
def user_access(user_id: str, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """Явная картина доступов по человеку (§8.3 — не «роли-ярлыки»)."""
    require_top_owner(principal)
    grants = db.query(AccessGrant).filter(AccessGrant.user_id == user_id).all()
    out = []
    for g in grants:
        p = db.query(Permission).filter(Permission.id == g.permission_id).first()
        out.append({
            "grant_id": g.id, "active": g.active, "business_id": g.business_id,
            "resource": p.resource if p else None, "action": p.action if p else None, "scope": p.scope if p else None,
        })
    return {"user_id": user_id, "grants": out}


# ================= Управление доступом (§8.2 защита владельцев) =================
@router.post("/access", status_code=201)
def manage_access(data: AccessIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)

    target_owner = get_owner(db, data.user_id)
    # Отключение доступа владельцу — только с согласия другого владельца (§8.2)
    if target_owner is not None and data.active is False:
        ap = approvals_service.create_approval(
            db, kind="disable_access", ref_id=data.user_id, amount=None,
            note=f"Отключение доступа владельцу {data.user_id} (нужно согласие другого владельца)", actor_id=principal.id,
        )
        db.commit()
        return {"pending_approval": serialize(ap), "message": "Требуется согласие другого владельца (§8.2)"}

    perm = db.query(Permission).filter(
        Permission.resource == data.resource, Permission.action == data.action, Permission.scope == data.scope
    ).first()
    if perm is None:
        perm = Permission(resource=data.resource, action=data.action, scope=data.scope)
        db.add(perm)
        db.flush()

    grant = db.query(AccessGrant).filter(
        AccessGrant.user_id == data.user_id, AccessGrant.permission_id == perm.id
    ).first()
    if grant is None:
        grant = AccessGrant(user_id=data.user_id, permission_id=perm.id, business_id=data.business_id,
                            granted_by=principal.id, active=data.active, created_by=principal.id)
        db.add(grant)
    else:
        grant.active = data.active
        if not data.active:
            grant.disabled_by = principal.id
            grant.disabled_at = now_utc()
    db.flush()
    write_audit(db, user_id=principal.id, action="disable_access" if not data.active else "create",
                resource="access", ref_id=data.user_id, after=data.model_dump())
    db.commit()
    db.refresh(grant)
    return serialize(grant)


# ================= Согласования троих (§8.2) =================
@router.get("/approvals")
def list_approvals(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.APPROVAL, Action.APPROVE)
    return serialize_list(db.query(Approval).order_by(Approval.created_at.desc()).all())


@router.post("/approvals", status_code=201)
def create_approval(data: ApprovalCreateIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    principal.require(Resource.APPROVAL, Action.APPROVE)
    ap = approvals_service.create_approval(db, kind=data.kind, ref_id=data.ref_id, amount=data.amount, note=data.note, actor_id=principal.id)
    db.commit()
    return serialize(ap)


def _apply_disable_access(db: Session, *, target_user_id: str, actor_id: str, approval: Approval) -> None:
    """Фактическое отключение доступа владельцу после согласия другого владельца (§8.2)."""
    user = db.query(User).filter(User.id == target_user_id).first()
    if user:
        user.is_active = False  # реальное отключение доступа
    for g in db.query(AccessGrant).filter(AccessGrant.user_id == target_user_id, AccessGrant.active.is_(True)).all():
        g.active = False
        g.disabled_by = actor_id
        g.disabled_at = now_utc()
    approval.result = "approved"
    write_audit(db, user_id=actor_id, action="disable_access", resource="access", ref_id=target_user_id,
                after={"is_active": False, "by": actor_id})
    db.commit()


@router.post("/approvals/{approval_id}/vote")
def vote(approval_id: str, data: VoteIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    ap = db.query(Approval).filter(Approval.id == approval_id).first()
    if ap is None:
        raise not_found("Согласование не найдено")

    # Отключение доступа владельцу — с согласия ДРУГОГО владельца (§8.2)
    if ap.kind == "disable_access":
        if not principal.is_owner:
            raise forbidden("Голосовать могут только владельцы")
        if principal.id == ap.ref_id:
            raise forbidden("Владелец не может согласовывать отключение самого себя")
        result = approvals_service.vote(db, actor=principal, approval_id=approval_id, decision=data.decision)
        if data.decision == "yes":
            _apply_disable_access(db, target_user_id=ap.ref_id, actor_id=principal.id, approval=result)
        return serialize(result)

    # Обычный путь: согласие всех троих
    ap = approvals_service.vote(db, actor=principal, approval_id=approval_id, decision=data.decision)
    if ap.result == "approved" and ap.kind == "purchase" and ap.ref_id:
        from app.db.models import Purchase

        pur = db.query(Purchase).filter(Purchase.id == ap.ref_id).first()
        if pur:
            pur.status = "approved"
            db.commit()
    return serialize(ap)


# ================= Задачи (§8.2) =================
@router.get("/tasks")
def list_tasks(page: int = 1, size: int = 50, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    q = db.query(Task)
    # Владельцы Сохиб/Ифтихор видят все; остальные — назначенные им
    if not (principal.is_owner and principal.owner_type in (OwnerType.SOHIB, OwnerType.IFTIKHOR)):
        q = q.filter((Task.assigned_to == principal.id) | (Task.assigned_by == principal.id))
    return paginate(q.order_by(Task.created_at.desc()), page, size)


@router.post("/tasks", status_code=201)
def create_task(data: TaskIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    # Сохиб/Ифтихор — всем; Довуд — по своей зоне (§8.2)
    if principal.is_owner and principal.owner_type in (OwnerType.SOHIB, OwnerType.IFTIKHOR):
        pass
    else:
        principal.require(Resource.TASK, Action.ASSIGN_TASK, business_id=data.business_scope)
    due = None
    if data.due_at:
        try:
            due = datetime.fromisoformat(data.due_at)
        except ValueError:
            raise bad_request("bad_date", "due_at должен быть ISO-датой")
    task = Task(assigned_to=data.assigned_to, assigned_by=principal.id, title=data.title,
                description=data.description, business_scope=data.business_scope, due_at=due, created_by=principal.id)
    db.add(task)
    db.flush()
    write_audit(db, user_id=principal.id, action="assign_task", resource="task", ref_id=task.id, after={"assigned_to": data.assigned_to, "title": data.title})
    db.commit()
    db.refresh(task)
    from app.realtime import channels
    from app.realtime.publisher import publish
    publish(channels.employee(data.assigned_to), "task.assigned", {"id": task.id, "title": task.title})
    return serialize(task)


@router.post("/tasks/{task_id}/status")
def set_task_status(task_id: str, data: TaskStatusIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise not_found("Задача не найдена")
    if task.assigned_to != principal.id and task.assigned_by != principal.id and not principal.is_owner:
        raise forbidden("Нельзя менять чужую задачу")
    task.status = data.status
    write_audit(db, user_id=principal.id, action="update_via_reversal", resource="task", ref_id=task.id, after={"status": data.status})
    db.commit()
    return serialize(task)


# ================= Календарь (§8.3) =================
@router.get("/calendar")
def list_calendar(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)
    return serialize_list(db.query(CalendarEvent).order_by(CalendarEvent.at).all())


@router.post("/calendar", status_code=201)
def create_event(data: CalendarIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    require_top_owner(principal)
    at = None
    if data.at:
        try:
            at = datetime.fromisoformat(data.at)
        except ValueError:
            raise bad_request("bad_date", "at должен быть ISO-датой")
    ev = CalendarEvent(owner_scope=data.owner_scope, type=data.type, title=data.title, at=at,
                       participants_json=data.participants, created_by=principal.id)
    db.add(ev)
    db.flush()
    write_audit(db, user_id=principal.id, action="create", resource="calendar", ref_id=ev.id, after={"title": data.title})
    db.commit()
    db.refresh(ev)
    return serialize(ev)
