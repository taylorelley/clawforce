# specops_lib

Shared technical library for the SpecOps ecosystem.

## Installation

```bash
pip install specops_lib
```

## What's Included

- **Storage backends** — Local filesystem and S3 storage abstractions
- **Configuration** — Pydantic-based config schema and YAML/JSON loader
- **Activity tracking** — Event logging for agent activity streams
- **Registry** — Skill (agentskill.sh), MCP (official registry), and Software (marketplace YAML) registries

## Usage

This package is typically installed as a dependency of `specialagent` or `specops`. For direct usage:

```python
from specops_lib.storage import get_storage_backend
from specops_lib.config import load_config
from specops_lib.activity import ActivityLog, ActivityEvent
```

## Part of SpecOps

This is a component of the [SpecOps](https://github.com/taylorelley/specops) multi-agent platform.

- **specops_lib** — Shared library (this package)
- **specialagent** — AI agent worker framework
- **specops** — Admin control plane and dashboard

## License

Apache 2.0
