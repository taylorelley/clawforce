"""Engine-swap test: confirm GuardrailsConfig.engine='defenseclaw' substitutes
defenseclaw guardrails for the built-in regex/LLM resolution path."""

from __future__ import annotations

from specialagent.agent.loop.core import _build_defenseclaw_guardrails
from specops_lib.config.schema import (
    DefenseClawConfig,
    GuardrailRef,
    GuardrailsConfig,
    ToolsConfig,
)
from specops_lib.guardrails import DefenseClawGuardrail


def test_default_engine_is_builtin() -> None:
    cfg = GuardrailsConfig()
    assert cfg.engine == "builtin"
    assert cfg.defenseclaw is None


def test_defenseclaw_engine_builds_three_position_guardrails() -> None:
    dc = DefenseClawConfig(gateway_url="http://gw.test", api_key="t", policy_pack="default")
    tool_g, default_tool_g, agent_out_g = _build_defenseclaw_guardrails(dc, agent_id="a1")
    # Per-tool overrides are bypassed under the global swap.
    assert tool_g == {}
    assert len(default_tool_g) == 1
    assert isinstance(default_tool_g[0], DefenseClawGuardrail)
    assert len(agent_out_g) == 1
    assert isinstance(agent_out_g[0], DefenseClawGuardrail)
    # Distinct names so retry counters and event IDs don't collide.
    assert default_tool_g[0].name == "defenseclaw_tool"
    assert agent_out_g[0].name == "defenseclaw_agent_output"


def test_defenseclaw_on_fail_default_is_raise() -> None:
    dc = DefenseClawConfig(gateway_url="http://gw.test")
    _, default_tool_g, agent_out_g = _build_defenseclaw_guardrails(dc, agent_id="a1")
    assert default_tool_g[0].on_fail == "raise"
    assert agent_out_g[0].on_fail == "raise"


def test_defenseclaw_on_fail_override() -> None:
    dc = DefenseClawConfig(gateway_url="http://gw.test", on_fail="escalate")
    _, default_tool_g, _ = _build_defenseclaw_guardrails(dc, agent_id="a1")
    assert default_tool_g[0].on_fail == "escalate"


def test_defenseclaw_on_fail_invalid_falls_back_to_raise() -> None:
    dc = DefenseClawConfig(gateway_url="http://gw.test", on_fail="bogus")
    _, default_tool_g, _ = _build_defenseclaw_guardrails(dc, agent_id="a1")
    assert default_tool_g[0].on_fail == "raise"


def test_per_tool_refs_are_ignored_under_swap() -> None:
    """Sanity: even if the operator left tools.guardrails populated,
    the swap returns an empty per-tool map and a single defenseclaw
    instance covers all tools."""
    # Build a ToolsConfig with refs that would normally produce regex guardrails.
    tools = ToolsConfig(guardrails=[GuardrailRef(name="any", pattern="secret")])
    dc = DefenseClawConfig(gateway_url="http://gw.test")
    tool_g, default_tool_g, _ = _build_defenseclaw_guardrails(dc, agent_id="a1")
    assert tool_g == {}
    # Only the defenseclaw instance — the regex ref didn't materialise.
    assert len(default_tool_g) == 1
    assert isinstance(default_tool_g[0], DefenseClawGuardrail)
    # ToolsConfig itself is unchanged (the refs are still there in YAML);
    # the swap just doesn't consume them.
    assert tools.guardrails[0].pattern == "secret"
