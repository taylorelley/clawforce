"""Forward :class:`ActivityEvent` stream to the defenseclaw gateway audit sink.

A small fire-and-forget pump: callers enqueue serialised events; a
background task drains the queue and POSTs each one. Drops on
backpressure (bounded queue) so the agent loop is never blocked by a
slow gateway.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_QUEUE_MAX = 2000


class DefenseClawAuditForwarder:
    """Background pump that ships activity events to defenseclaw.

    Lifecycle: ``start()`` from the worker bootstrap once an event loop
    is running; ``enqueue(event)`` for each :class:`ActivityEvent`;
    ``close()`` during shutdown to flush in-flight items and cancel the
    drain task.
    """

    def __init__(
        self,
        *,
        gateway_url: str,
        agent_id: str,
        api_key: str = "",
        timeout_seconds: float = 5.0,
    ) -> None:
        self._url = gateway_url.rstrip("/") + "/v1/audit/events"
        self._agent_id = agent_id
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=_QUEUE_MAX)
        self._task: asyncio.Task[None] | None = None
        self._closed = False

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._drain(), name="defenseclaw-audit")

    def enqueue(self, event: Any) -> None:
        """Best-effort enqueue. Dropping on full queue is intentional —
        audit forwarding must never block the producer side."""
        if self._closed:
            return
        item = _to_dict(event)
        # Forwarder is per-agent; authoritative for the audit tag.
        item["agent_id"] = self._agent_id
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            logger.warning(
                "[defenseclaw.audit] queue full (>%d); dropping event %s",
                _QUEUE_MAX,
                item.get("event_type"),
            )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()

    async def _drain(self) -> None:
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                item = await self._queue.get()
                if item is None:
                    break
                try:
                    await client.post(self._url, json=item, headers=headers)
                except (httpx.HTTPError, OSError) as exc:
                    logger.warning("[defenseclaw.audit] post failed: %s", exc)


def _to_dict(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return dict(event)
    if is_dataclass(event):
        return asdict(event)
    if hasattr(event, "model_dump"):
        return event.model_dump()  # pragma: no cover - pydantic fallback
    return {"raw": repr(event)}


__all__ = ["DefenseClawAuditForwarder"]
