# SpecOps

[![PyPI version](https://badge.fury.io/py/specops.svg)](https://badge.fury.io/py/specops)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Multi-agent team admin and control plane. Build teams of AI agents that collaborate on real work.

## Installation

```bash
pip install specops
```

This installs everything you need, including all messaging channels.

## Quick Start

```bash
# 1. Initialize and create admin user
specops setup

# 2. Start the server
specops serve

# Access dashboard at http://localhost:8080
```

## Features

- **Multi-Agent Teams** — Coordinate multiple AI agents on shared goals
- **Plan Boards** — Kanban-style task management with automatic notifications
- **Agent-to-Agent Communication** — Agents discover and message each other
- **Real-Time Dashboard** — Live view of agent activity and progress
- **Agent Runtimes** — Run agents as subprocesses or Docker containers
- **REST API** — Full API for plans, agents, and artifacts

## CLI Commands

```bash
# Setup & Server
specops setup                    # Initialize and create admin user
specops serve                    # Start on port 8080
specops serve --port 3000        # Custom port
specops serve --workers 4        # Production with multiple workers

# Agent Management
specops agent list               # List all agents
specops agent create --name "Agent Name" --template sre
specops agent start <id>         # Start an agent
specops agent stop <id>          # Stop an agent
specops agent token <id>         # Show agent connection token
specops agent token <id> --regenerate  # Rotate agent token

# User Management
specops user create <username>   # Create user (--password, --role)
specops user update <username>   # Update user (--password, --role)
specops user list               # List admin users
specops user set-password <username>   # Reset password
specops user reset <username>   # Reset password (alias)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SPECOPS                              │
│            Multi-Agent Admin & Control Plane                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Plan Board │  │ Agent Runtimes│  │  WebSocket Hub   │   │
│  │  (Kanban)   │  │ (proc/docker)│  │ (req/resp + RT)  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                       SPECIALAGENT                               │
│              Lightweight Agent Workers                      │
├─────────────────────────────────────────────────────────────┤
│                       SPECOPS_LIB                               │
│              Shared Infrastructure                          │
└─────────────────────────────────────────────────────────────┘
```

## Docker Deployment

```bash
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./data:/data \
  ghcr.io/taylorelley/specops:latest
```

## Documentation

Full documentation: https://github.com/taylorelley/specops

See [Product Principles & Best Practices](https://taylorelley.github.io/specops/guide/principles) for our focus on easy agent team setup, MCP over Computer/Browser Use, and security best practices.

## License

Apache 2.0
