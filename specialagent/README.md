# specialagent

A lightweight AI agent framework modified from nanobot, featuring tools, messaging channels, and LLM providers.

## Installation

```bash
pip install specialagent
```

**With messaging channels:**

```bash
pip install specialagent[telegram]      # Telegram support
pip install specialagent[slack]         # Slack support
pip install specialagent[all-channels]  # All channels
```

See [docs/CHANNELS_SETUP.md](../docs/CHANNELS_SETUP.md) for channel-specific setup (Slack, etc.).

## Features

- **Agent Tools** — Filesystem, shell, web search, MCP integration
- **Messaging Channels** — Telegram, Slack, Discord, Feishu, WhatsApp, Email
- **LLM Providers** — Any provider via LiteLLM (OpenAI, Anthropic, etc.)
- **Skills System** — Extensible agent capabilities
- **Cron Scheduling** — Recurring tasks and heartbeats

## Quick Start

```bash
# Initialize a new agent
specialagent init ./my-agent

# Start the agent worker
specialagent run --agent-root ./my-agent
```

## CLI Commands

```bash
specialagent init <path>                          # Create agent directory
specialagent run --agent-root <path>              # Start agent worker
specialagent run --agent-root <path> \
  --admin-url <url> --token <token>          # Connect to a SpecOps control plane
specialagent config --agent-root <path>           # View agent configuration
specialagent config --agent-root <path> --edit    # Open config in editor
specialagent version                              # Show version
```

## Part of SpecOps

This is a component of the [SpecOps](https://github.com/taylorelley/specops) multi-agent platform.

For team coordination with multiple agents, plans, and a web dashboard, install:

```bash
pip install specops
```

## License

Apache 2.0
