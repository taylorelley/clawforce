"""DefenseClawGuardrail tests with a stubbed httpx.AsyncClient — no real network."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from specops_lib.guardrails import (
    DefenseClawGuardrail,
    DefenseClawSettings,
    GuardrailContext,
)
from specops_lib.guardrails import defenseclaw as dc_mod

_CTX = GuardrailContext(
    position="tool_input",
    tool_name="exec",
    args={"cmd": "rm -rf /"},
    execution_id="exec1",
    step_id="step1",
)


class _StubResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | str | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = payload if isinstance(payload, str) else json.dumps(payload or {})

    def json(self) -> Any:
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload or {}


class _StubClient:
    """Minimal stand-in for ``httpx.AsyncClient`` that records the last call."""

    last_url: str | None = None
    last_payload: dict[str, Any] | None = None
    last_headers: dict[str, str] | None = None

    def __init__(self, response: _StubResponse | Exception) -> None:
        self._response = response

    async def __aenter__(self) -> "_StubClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def post(self, url: str, *, json: Any, headers: dict[str, str]) -> _StubResponse:
        type(self).last_url = url
        type(self).last_payload = json
        type(self).last_headers = headers
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def _patch_client(monkeypatch: pytest.MonkeyPatch, response: _StubResponse | Exception) -> None:
    """Replace httpx.AsyncClient inside the adapter module with our stub."""

    def _factory(*_a: Any, **_kw: Any) -> _StubClient:
        return _StubClient(response)

    monkeypatch.setattr(dc_mod.httpx, "AsyncClient", _factory)


def _settings(**overrides: Any) -> DefenseClawSettings:
    base = {
        "gateway_url": "http://gw.test",
        "api_key": "tok",
        "policy_pack": "default",
        "timeout_seconds": 1.0,
        "fail_closed": True,
    }
    base.update(overrides)
    return DefenseClawSettings(**base)


class TestDefenseClawGuardrail:
    async def test_allow_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, _StubResponse(200, {"decision": "allow", "reason": "ok"}))
        g = DefenseClawGuardrail(position="tool_input", settings=_settings(), agent_id="a1")
        result = await g.check_async("anything", _CTX)
        assert result.passed is True

    async def test_block_fails_with_reason(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(
            monkeypatch, _StubResponse(200, {"decision": "block", "reason": "rm -rf forbidden"})
        )
        g = DefenseClawGuardrail(position="tool_input", settings=_settings(), agent_id="a1")
        result = await g.check_async("anything", _CTX)
        assert result.passed is False
        assert "rm -rf" in result.message

    async def test_fix_returns_fixed_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(
            monkeypatch,
            _StubResponse(
                200,
                {"decision": "fix", "reason": "redacted", "fixed_output": "[REDACTED]"},
            ),
        )
        g = DefenseClawGuardrail(position="tool_output", settings=_settings(), agent_id="a1")
        result = await g.check_async("secret data", _CTX)
        assert result.passed is False
        assert result.fixed_output == "[REDACTED]"

    async def test_unknown_decision_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, _StubResponse(200, {"decision": "yolo"}))
        g = DefenseClawGuardrail(position="tool_input", settings=_settings(), agent_id="a1")
        result = await g.check_async("x", _CTX)
        assert result.passed is False
        assert "unexpected decision" in result.message

    async def test_payload_carries_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, _StubResponse(200, {"decision": "allow"}))
        g = DefenseClawGuardrail(position="tool_input", settings=_settings(), agent_id="a1")
        await g.check_async("hello", _CTX)
        payload = _StubClient.last_payload or {}
        assert payload["position"] == "tool_input"
        assert payload["tool_name"] == "exec"
        assert payload["agent_id"] == "a1"
        assert payload["policy_pack"] == "default"
        assert _StubClient.last_headers["authorization"] == "Bearer tok"
        assert _StubClient.last_url.endswith("/v1/guardrail/evaluate")

    async def test_fail_closed_blocks_on_connection_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_client(monkeypatch, httpx.ConnectError("refused"))
        g = DefenseClawGuardrail(
            position="tool_input", settings=_settings(fail_closed=True), agent_id="a1"
        )
        result = await g.check_async("x", _CTX)
        assert result.passed is False
        assert "unreachable" in result.message

    async def test_fail_open_allows_on_connection_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_client(monkeypatch, httpx.ConnectError("refused"))
        g = DefenseClawGuardrail(
            position="tool_input", settings=_settings(fail_closed=False), agent_id="a1"
        )
        result = await g.check_async("x", _CTX)
        assert result.passed is True

    async def test_5xx_treated_as_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, _StubResponse(503, "upstream down"))
        g = DefenseClawGuardrail(
            position="tool_input", settings=_settings(fail_closed=True), agent_id="a1"
        )
        result = await g.check_async("x", _CTX)
        assert result.passed is False
        assert "503" in result.message

    async def test_4xx_surfaces_body_as_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, _StubResponse(400, "bad policy"))
        g = DefenseClawGuardrail(position="tool_input", settings=_settings(), agent_id="a1")
        result = await g.check_async("x", _CTX)
        assert result.passed is False
        assert "400" in result.message

    def test_sync_check_raises(self) -> None:
        g = DefenseClawGuardrail(position="tool_input", settings=_settings(), agent_id="a1")
        with pytest.raises(NotImplementedError):
            g.check("x", _CTX)
