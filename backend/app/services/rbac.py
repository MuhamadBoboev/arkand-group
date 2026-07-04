"""RBAC (§8): загрузка прав, проверка scope, защита владельцев.

Проверка прав — на бэке (§8.5, §14). Фронт лишь скрывает недоступное.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.constants import Action, OwnerType, Resource, Scope
from app.core.errors import forbidden
from app.db.models import (
    AccessGrant,
    Owner,
    Permission,
    RolePermission,
    User,
    UserRole,
)

# permission-триплет
Triple = tuple[str, str, str]

# Сентинел: «объект не указан» (проверка возможности/список) vs явный владелец объекта (мутация).
_UNSET = object()


def get_owner(db: Session, user_id: str) -> Owner | None:
    return db.query(Owner).filter(Owner.user_id == user_id).first()


def get_user_businesses(db: Session, user_id: str) -> set[str]:
    """Бизнесы, к которым привязан пользователь (для scope own_business)."""
    out: set[str] = set()
    from app.db.models import Employee

    for e in db.query(Employee).filter(Employee.user_id == user_id).all():
        if e.business_id:
            out.add(e.business_id)
    for g in db.query(AccessGrant).filter(AccessGrant.user_id == user_id, AccessGrant.active.is_(True)).all():
        if g.business_id:
            out.add(g.business_id)
    return out


def load_permissions(db: Session, user_id: str) -> set[Triple]:
    """Права из ролей + активные индивидуальные гранты (отключённые исключены)."""
    perms: set[Triple] = set()

    # из ролей
    role_ids = [r.role_id for r in db.query(UserRole).filter(UserRole.user_id == user_id).all()]
    if role_ids:
        perm_ids = [
            rp.permission_id
            for rp in db.query(RolePermission).filter(RolePermission.role_id.in_(role_ids)).all()
        ]
        if perm_ids:
            for p in db.query(Permission).filter(Permission.id.in_(perm_ids)).all():
                perms.add((p.resource, p.action, p.scope))

    # индивидуальные активные гранты (§8.3 — картина доступов по человеку)
    active_grants = db.query(AccessGrant).filter(
        AccessGrant.user_id == user_id, AccessGrant.active.is_(True)
    ).all()
    grant_perm_ids = [g.permission_id for g in active_grants]
    if grant_perm_ids:
        for p in db.query(Permission).filter(Permission.id.in_(grant_perm_ids)).all():
            perms.add((p.resource, p.action, p.scope))

    return perms


@dataclass
class Principal:
    """Контекст текущего пользователя для проверки прав в эндпоинтах."""
    user: User
    is_owner: bool = False
    owner_type: str | None = None
    permissions: set[Triple] = field(default_factory=set)
    businesses: set[str] = field(default_factory=set)

    @property
    def id(self) -> str:
        return self.user.id

    def _matching_scopes(self, resource: str, action: str) -> set[str]:
        scopes: set[str] = set()
        for (r, a, s) in self.permissions:
            r_ok = r in (resource, Resource.ALL)
            a_ok = a in (action, Action.ALL)
            if r_ok and a_ok:
                scopes.add(s)
        return scopes

    def can(
        self,
        resource: str,
        action: str,
        *,
        business_id: str | None = None,
        record_owner_id=_UNSET,
    ) -> bool:
        # Владельцы Сохиб/Ифтихор — полный доступ (§8.1). Довуд идёт по обычным permissions.
        if self.is_owner and self.owner_type in (OwnerType.SOHIB, OwnerType.IFTIKHOR):
            return True

        scopes = self._matching_scopes(resource, action)
        if not scopes:
            return False

        for s in scopes:
            if s == Scope.ALL:
                return True
            if s == Scope.READ_ONLY:
                if action == Action.VIEW:
                    return True
                continue
            if s == Scope.OWN_BUSINESS:
                # business_id не указан → проверка возможности (список); указан → должен входить в свои
                if business_id is None or business_id in self.businesses:
                    return True
                continue
            if s == Scope.OWN_RECORDS:
                # объект не указан (_UNSET) → проверка возможности; указан → должен принадлежать пользователю.
                # record_owner_id=None означает «объект без владельца» → для own_records доступ НЕ даётся.
                if record_owner_id is _UNSET or record_owner_id == self.user.id:
                    return True
                continue
        return False

    def require(
        self,
        resource: str,
        action: str,
        *,
        business_id: str | None = None,
        record_owner_id=_UNSET,
        message: str | None = None,
    ) -> None:
        if not self.can(resource, action, business_id=business_id, record_owner_id=record_owner_id):
            raise forbidden(message or f"Нет доступа: {resource}.{action}")


def build_principal(db: Session, user: User) -> Principal:
    owner = get_owner(db, user.id)
    return Principal(
        user=user,
        is_owner=owner is not None,
        owner_type=owner.owner_type if owner else None,
        permissions=load_permissions(db, user.id),
        businesses=get_user_businesses(db, user.id),
    )


# --- Защита владельцев (§8.2) ---
def assert_can_disable_access(db: Session, actor: Principal, target_user_id: str) -> None:
    """Отключить доступ владельцу можно только с согласия другого владельца.
    Обычных сотрудников Сохиб и Ифтихор отключают свободно.
    """
    target_owner = get_owner(db, target_user_id)
    actor_owner = actor.is_owner

    # Отключать доступ вправе только владельцы Сохиб/Ифтихор (полный доступ)
    if actor.owner_type not in (OwnerType.SOHIB, OwnerType.IFTIKHOR):
        raise forbidden("Управление доступом — только у Сохиба и Ифтихора")

    if target_owner is not None:
        # Цель — владелец: нужно согласие ДРУГОГО владельца (проверяется на уровне approvals).
        raise forbidden(
            "Отключение доступа владельцу требует согласия другого владельца (§8.2)"
        )
