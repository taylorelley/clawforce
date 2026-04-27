"""Cisco defenseclaw gateway adapter.

Implements :class:`Guardrail` against the defenseclaw gateway's runtime
inspection REST endpoint. The gateway evaluates ``(content, position,
tool_name, args)`` against its policy packs (Rego/YAML) and returns one
of ``allow`` / ``block`` / ``fix``. The adapter translates that into
:class:`GuardrailResult` so the existing :class:`GuardrailRunner` can
dispatch ``retry`` / ``raise`` / ``fix`` / ``escalate`` exactly as it
does for the built-in regex/LLM guardrails.

One instance is constructed per :class:`Position` at agent start (see
``specialagent/agent/loop/core.py``). Network errors are mapped to
``passed=fail_closed`` — when ``fail_closed=True`` (the default) the
agent halts on a missing gateway; when ``False`` the gateway being down
opens the door, which is the right call only for non-production use.

The exact gateway request/response schema is documented in
``docs/API.md`` of the upstream defenseclaw repo. The schema below
follows the conventions stated there at the time of integration; the
adapter tolerates extra fields and missing optional ones so a minor
gateway version drift does not break agents.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from specops_lib.guardrails.base import (
    Guardrail,
    GuardrailContext,
    GuardrailResult,
    OnFail,
    Position,
)

logger = logging.getLogger(__name__)


@dataclass
class DefenseClawSettings:
    """Runtime settings sliced from :class:`DefenseClawConfig`.

    Held separately from the schema so this module has no Pydantic
    dependency and the adapter is trivially testable.
    """

    gateway_url: str
    api_key: str = ""
    policy_pack: str = ""
    timeout_seconds: float = 5.0
    fail_closed: bool = True


class DefenseClawGuardrail(Guardrail):
    """Guardrail that delegates the decision to a defenseclaw gateway.

    Pure async — :meth:`check` raises ``NotImplementedError`` and the
    runner picks up :meth:`check_async` (the same convention
    :class:`LLMGuardrail` uses).
    """

    def __init__(
        self,
        *,
        position: Position,
        settings: DefenseClawSettings,
        agent_id: str = "",
        name: str | None = None,
        on_fail: OnFail = "raise",
        max_retries: int = 1,
    ) -> None:
        super().__init__(
            name=name or f"defenseclaw_{position}",
            on_fail=on_fail,
            max_retries=max_retries,
        )
        self._position: Position = position
        self._settings = settings
        self._agent_id = agent_id

    def check(self, content: str, context: GuardrailContext) -> GuardrailResult:
        raise NotImplementedError(
            "DefenseClawGuardrail.check() is async; runner uses check_async()."
        )

    async def check_async(self, content: str, context: GuardrailContext) -> GuardrailResult:
        url = self._settings.gateway_url.rstrip("/") + "/v1/guardrail/evaluate"
        headers = {"content-type": "application/json"}
        if self._settings.api_key:
            headers["authorization"] = f"Bearer {self._settings.api_key}"
        payload: dict[str, Any] = {
            "position": context.position,
            "content": content,
            "policy_pack": self._settings.policy_pack or None,
            "agent_id": self._agent_id,
            "tool_name": context.tool_name,
            "args": _safe_args(context.args),
            "execution_id": context.execution_id,
            "step_id": context.step_id,
        }
        try:
            async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except (httpx.HTTPError, OSError) as exc:
            return self._unreachable_result(f"defenseclaw gateway unreachable: {exc}")
        if resp.status_code >= 500:
            return self._unreachable_result(
                f"defenseclaw gateway returned {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code >= 400:
            # 4xx is a client/policy mistake; treat as fail and surface the body.
            return GuardrailResult(
                passed=False,
                message=f"defenseclaw gateway rejected request ({resp.status_code}): "
                f"{resp.text[:200]}",
            )
        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            return GuardrailResult(
                passed=False,
                message=f"defenseclaw gateway returned non-JSON body: {exc}",
            )
        return _parse_decision(data)

    def _unreachable_result(self, message: str) -> GuardrailResult:
        if self._settings.fail_closed:
            return GuardrailResult(passed=False, message=message)
        logger.warning("[guardrail.defenseclaw] %s — fail_closed=False; allowing", message)
        return GuardrailResult(passed=True, message=message)


def _safe_args(args: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Normalise tool args to plain JSON-able dicts; defenseclaw will redact."""
    if args is None:
        return None
    out: dict[str, Any] = {}
    for k, v in args.items():
        try:
            json.dumps(v)
            out[str(k)] = v
        except TypeError:
            out[str(k)] = repr(v)
    return out


def _parse_decision(data: Any) -> GuardrailResult:
    """Translate gateway response → :class:`GuardrailResult`.

    Expected shape (tolerant): ``{"decision": "allow"|"block"|"fix",
    "reason": str, "fixed_output": str?}``. ``allow`` → passed=True;
    ``block`` and ``fix`` → passed=False with the appropriate fields.
    Anything else falls through as a fail with the raw decision in the
    message.
    """
    if not isinstance(data, dict):
        return GuardrailResult(passed=False, message="defenseclaw returned non-object JSON")
    decision = str(data.get("decision") or "").lower()
    reason = str(data.get("reason") or "")
    fixed = data.get("fixed_output")
    if fixed is not None and not isinstance(fixed, str):
        fixed = str(fixed)
    if decision == "allow":
        return GuardrailResult(passed=True, message=reason)
    if decision == "fix":
        if not fixed:
            return GuardrailResult(
                passed=False,
                message=reason or "defenseclaw returned fix decision without fixed_output",
            )
        return GuardrailResult(
            passed=False, message=reason or "defenseclaw fix", fixed_output=fixed
        )
    if decision == "block":
        return GuardrailResult(passed=False, message=reason or "defenseclaw blocked")
    return GuardrailResult(
        passed=False,
        message=f"defenseclaw returned unexpected decision '{decision}'",
    )


__all__ = ["DefenseClawGuardrail", "DefenseClawSettings"]
