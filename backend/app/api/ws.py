"""WebSocket /ws (§12): авторизация JWT → подписка на каналы по правам → реалтайм."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.constants import Action, Resource
from app.core.security import decode_token
from app.db.base import SessionLocal
from app.db.models import CashRegister, User
from app.realtime.manager import manager
from app.services.rbac import build_principal

router = APIRouter()


def _channel_allowed(principal, channel: str, db) -> bool:
    """Клиент подписан только на доступное по правам (§12)."""
    if principal.is_owner and principal.owner_type in ("sohib", "iftikhor"):
        return True
    if channel.startswith("business:"):
        bid = channel.split(":", 1)[1]
        return bid in principal.businesses or principal.can(Resource.OBJECT, Action.VIEW, business_id=bid) \
            or principal.can(Resource.ORDER, Action.VIEW, business_id=bid) \
            or principal.can(Resource.AUDIT, Action.VIEW)
    if channel.startswith("cash:"):
        cid = channel.split(":", 1)[1]
        c = db.query(CashRegister).filter(CashRegister.id == cid).first()
        if not c:
            return False
        return principal.can(Resource.CASH, Action.VIEW, business_id=c.business_id, record_owner_id=c.responsible_user_id)
    if channel.startswith("employee:"):
        uid = channel.split(":", 1)[1]
        return uid == principal.id
    if channel == "finance":
        return principal.can(Resource.CASH, Action.VIEW)
    if channel == "supply":
        return principal.can(Resource.SUPPLY_REQUEST, Action.VIEW) or principal.can(Resource.PURCHASE, Action.VIEW)
    if channel == "owners":
        return principal.is_owner
    if channel == "audit":
        return principal.can(Resource.AUDIT, Action.VIEW)
    return False


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # 1) Приём соединения и авторизация по JWT (token в query или первым сообщением)
    token = ws.query_params.get("token")
    conn = None
    db = SessionLocal()
    try:
        if not token:
            await ws.accept()
            first = await ws.receive_json()
            if first.get("type") == "auth":
                token = first.get("token")
            if not token:
                await ws.close(code=4401)
                return
            accepted_already = True
        else:
            accepted_already = False

        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise ValueError("not access")
            user = db.query(User).filter(User.id == payload.get("sub")).first()
            if user is None or not user.is_active:
                raise ValueError("no user")
        except Exception:
            if accepted_already:
                await ws.close(code=4401)
            else:
                await ws.accept()
                await ws.close(code=4401)
            return

        principal = build_principal(db, user)

        if accepted_already:
            # ws уже принят (чтобы прочитать auth-сообщение) — регистрируем соединение вручную
            from app.realtime.manager import Connection

            conn = Connection(ws=ws, user_id=user.id)
            await manager.register(conn)
        else:
            conn = await manager.connect(ws, user.id)

        await ws.send_json({"type": "connected", "user_id": user.id})

        # 2) Цикл сообщений: subscribe / unsubscribe / ping
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")
            if mtype == "subscribe":
                requested = msg.get("channels", [])
                allowed = [ch for ch in requested if _channel_allowed(principal, ch, db)]
                manager.subscribe(conn, allowed)
                await ws.send_json({"type": "subscribed", "channels": sorted(conn.channels)})
            elif mtype == "unsubscribe":
                manager.unsubscribe(conn, msg.get("channels", []))
                await ws.send_json({"type": "unsubscribed", "channels": sorted(conn.channels)})
            elif mtype == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if conn is not None:
            await manager.disconnect(conn)
        db.close()
