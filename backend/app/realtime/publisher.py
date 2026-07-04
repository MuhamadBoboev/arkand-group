"""Publisher реалтайм-событий (§6.2, §12).

- Если задан REDIS_URL — публикуем в Redis Pub/Sub (масштабирование на несколько инстансов),
  а фоновый subscriber рассылает событие локальным WS-подписчикам.
- Если Redis нет — прямой in-process broadcast (локальная разработка/тесты).

Событие: {channel, type, payload, at}. Вызывается из sync-эндпоинтов, поэтому корутины
планируются на главный event loop через run_coroutine_threadsafe (безопасно из threadpool).
"""
from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.db.base import now_utc
from app.realtime.manager import manager

_REDIS_CHANNEL = "arkand-events"

_loop: asyncio.AbstractEventLoop | None = None
_redis = None  # type: ignore
_sub_task: asyncio.Task | None = None


def build_event(channel: str, type_: str, payload: dict) -> dict:
    return {"channel": channel, "type": type_, "payload": payload, "at": now_utc().isoformat()}


async def init_publisher(loop: asyncio.AbstractEventLoop) -> None:
    """Вызывается на старте приложения (§12)."""
    global _loop, _redis, _sub_task
    _loop = loop
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis

            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            _sub_task = loop.create_task(_redis_subscribe_loop())
        except Exception:
            _redis = None  # деградация до in-process


async def shutdown_publisher() -> None:
    global _sub_task, _redis
    if _sub_task:
        _sub_task.cancel()
    if _redis:
        try:
            await _redis.close()
        except Exception:
            pass


async def _redis_subscribe_loop() -> None:
    assert _redis is not None
    pubsub = _redis.pubsub()
    await pubsub.subscribe(_REDIS_CHANNEL)
    async for msg in pubsub.listen():
        if msg.get("type") != "message":
            continue
        try:
            event = json.loads(msg["data"])
            await manager.broadcast(event["channel"], event)
        except Exception:
            continue


def publish(channel: str, type_: str, payload: dict) -> None:
    """Опубликовать событие. Не бросает исключений наружу — реалтайм не ломает транзакцию."""
    event = build_event(channel, type_, payload)
    if _loop is None:
        return
    try:
        if _redis is not None:
            asyncio.run_coroutine_threadsafe(
                _redis.publish(_REDIS_CHANNEL, json.dumps(event)), _loop
            )
        else:
            asyncio.run_coroutine_threadsafe(manager.broadcast(channel, event), _loop)
    except Exception:
        pass


def publish_many(channels: list[str], type_: str, payload: dict) -> None:
    for ch in channels:
        publish(ch, type_, payload)
