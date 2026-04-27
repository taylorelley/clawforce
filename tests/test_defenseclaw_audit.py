"""DefenseClawAuditForwarder tests: enqueue / drain / drop / close."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from specops_lib.activity import ActivityEvent
from specops_lib.observability import DefenseClawAuditForwarder
from specops_lib.observability import defenseclaw_audit as audit_mod


class _RecordingClient:
    posts: list[tuple[str, dict[str, Any], dict[str, str]]] = []
    raise_on_post: Exception | None = None

    def __init__(self, *_a: Any, **_kw: Any) -> None:
        pass

    async def __aenter__(self) -> "_RecordingClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> Any:
        if type(self).raise_on_post is not None:
            raise type(self).raise_on_post
        type(self).posts.append((url, json, headers))

        class _OK:
            status_code = 200

        return _OK()


@pytest.fixture(autouse=True)
def _patch_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingClient.posts = []
    _RecordingClient.raise_on_post = None
    monkeypatch.setattr(audit_mod.httpx, "AsyncClient", _RecordingClient)


def _event(**overrides: Any) -> ActivityEvent:
    base = {"agent_id": "", "event_type": "tool_call", "channel": "", "content": "x"}
    base.update(overrides)
    return ActivityEvent(**base)


class TestDefenseClawAuditForwarder:
    async def test_enqueue_drains_to_post(self) -> None:
        fwd = DefenseClawAuditForwarder(gateway_url="http://gw.test", agent_id="a1", api_key="tok")
        fwd.start()
        fwd.enqueue(_event())
        # Give the drain task one tick to run.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fwd.close()
        assert len(_RecordingClient.posts) == 1
        url, payload, headers = _RecordingClient.posts[0]
        assert url == "http://gw.test/v1/audit/events"
        assert payload["agent_id"] == "a1"
        assert payload["event_type"] == "tool_call"
        assert headers["authorization"] == "Bearer tok"

    async def test_enqueue_after_close_is_silent(self) -> None:
        fwd = DefenseClawAuditForwarder(gateway_url="http://gw.test", agent_id="a1")
        fwd.start()
        await fwd.close()
        # Should not raise, should not post.
        fwd.enqueue(_event())
        assert _RecordingClient.posts == []

    async def test_post_failure_is_swallowed(self) -> None:
        _RecordingClient.raise_on_post = httpx.ConnectError("nope")
        fwd = DefenseClawAuditForwarder(gateway_url="http://gw.test", agent_id="a1")
        fwd.start()
        fwd.enqueue(_event())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        # Forwarder must not crash on transport errors.
        await fwd.close()

    async def test_dataclass_event_serialised(self) -> None:
        fwd = DefenseClawAuditForwarder(gateway_url="http://gw.test", agent_id="a1")
        fwd.start()
        fwd.enqueue(
            _event(event_type="guardrail_result", content="defenseclaw_tool@tool_input: fail")
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fwd.close()
        assert len(_RecordingClient.posts) == 1
        _, payload, _ = _RecordingClient.posts[0]
        assert payload["event_type"] == "guardrail_result"

    async def test_forwarder_overrides_event_agent_id(self) -> None:
        """Forwarder is per-agent; it tags every event with its own
        agent_id even if the producer passed something else."""
        fwd = DefenseClawAuditForwarder(gateway_url="http://gw.test", agent_id="a1")
        fwd.start()
        fwd.enqueue({"event_type": "custom", "agent_id": "stale"})
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fwd.close()
        assert len(_RecordingClient.posts) == 1
        _, payload, _ = _RecordingClient.posts[0]
        assert payload["agent_id"] == "a1"
        assert payload["event_type"] == "custom"
