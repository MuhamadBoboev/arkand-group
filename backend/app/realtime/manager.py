"""Менеджер WebSocket-подключений: подписки по каналам, broadcast (§12)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Connection:
    ws: WebSocket
    user_id: str
    channels: set[str] = field(default_factory=set)


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: list[Connection] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, user_id: str) -> Connection:
        await ws.accept()
        conn = Connection(ws=ws, user_id=user_id)
        async with self._lock:
            self._conns.append(conn)
        return conn

    async def register(self, conn: Connection) -> None:
        """Зарегистрировать уже принятый (accepted) сокет."""
        async with self._lock:
            self._conns.append(conn)

    async def disconnect(self, conn: Connection) -> None:
        async with self._lock:
            if conn in self._conns:
                self._conns.remove(conn)

    def subscribe(self, conn: Connection, channels: list[str]) -> None:
        conn.channels.update(channels)

    def unsubscribe(self, conn: Connection, channels: list[str]) -> None:
        conn.channels.difference_update(channels)

    async def broadcast(self, channel: str, message: dict) -> None:
        """Отправить событие всем подписчикам канала. Мёртвые соединения пропускаем."""
        targets = [c for c in list(self._conns) if channel in c.channels]
        for c in targets:
            try:
                await c.ws.send_json(message)
            except Exception:
                # соединение оборвалось — уберём (reconnect на клиенте §12)
                await self.disconnect(c)

    @property
    def count(self) -> int:
        return len(self._conns)


manager = ConnectionManager()
