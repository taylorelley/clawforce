# Guardrails: Cisco defenseclaw (optional)

SpecOps can route all guardrail decisions through Cisco's
[defenseclaw](https://github.com/cisco-ai-defense/defenseclaw) gateway
instead of the built-in regex / LLM / callable runners. This trades the
in-process Python checks for centralised policy authoring (Rego/YAML)
and a unified audit store (SQLite, JSONL, OTLP, Splunk, webhooks).

It is **off by default**. Built-in guardrails remain the recommended
path for most deployments — defenseclaw is the right choice when you
already standardise on Cisco's policy + audit story across multiple
agent platforms.

## How the swap works

The agent worker reads a top-level `guardrails` block at startup. When
`engine: defenseclaw`, the worker skips the normal `resolve_refs()`
path and substitutes a single `DefenseClawGuardrail` instance for tool
input/output and another for agent output. Per-tool, per-MCP, and
OpenAPI-tool guardrail refs in YAML are **bypassed** under the swap —
defenseclaw's policy packs are authoritative.

## Run the gateway

The gateway is a Go sidecar; SpecOps does **not** bundle it. Run it
out-of-band on the same host (or somewhere reachable):

```bash
defenseclaw-gateway start
```

Author a guardrail policy under `policies/guardrail/<pack>/` (see the
defenseclaw `docs/GUARDRAIL_RULE_PACKS.md`).

## Configure SpecOps

Add a top-level `guardrails` block to the agent YAML:

```yaml
guardrails:
  engine: defenseclaw
  defenseclaw:
    gateway_url: http://127.0.0.1:7890
    api_key: ${DEFENSECLAW_API_KEY}    # optional
    policy_pack: default
    timeout_seconds: 5.0
    fail_closed: true                  # block when gateway unreachable
    audit_forwarding: true             # ship activity events to gateway
    on_fail: raise                     # raise | retry | fix | escalate
```

`fail_closed: true` halts the agent if the gateway is unreachable; set
to `false` only for non-production smoke tests where availability
matters more than enforcement.

`audit_forwarding: true` mirrors every `ActivityEvent` to the
gateway's `/v1/audit/events` endpoint. Forwarding is fire-and-forget
with a bounded queue (2000 events): it never blocks the agent loop,
and on backpressure drops the **oldest** queued event to make room
for the new one — matching SpecOps' subscriber-broadcast convention
in `specops_lib/activity.py`.

## Rolling back

Set `engine: builtin` (or remove the block entirely) and restart the
worker. The built-in regex / LLM / callable runners reactivate using
your existing `tools.guardrails`, `agents.defaults.guardrails`,
per-MCP, and per-OpenAPI refs.

## Tradeoffs

- **Replace, not augment.** Under the swap, in-line YAML refs are
  ignored; if you have one team that wants regex guardrails alongside
  defenseclaw, keep `engine: builtin` and reference defenseclaw via a
  follow-up adapter. The current integration is intentionally scoped
  to a clean swap.
- **Sync vs async.** The adapter is pure async — the runner already
  prefers `check_async()` so existing retry/raise/fix/escalate
  semantics carry over without changes.
- **Sidecar deployment.** SpecOps does not run or supervise the
  gateway. If the gateway dies, every agent fails closed by default.
