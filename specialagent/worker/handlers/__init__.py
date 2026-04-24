"""Worker request handlers package.

Modules:
  schema.py      - Typed models for the worker ↔ admin WebSocket protocol
  filesystem.py  - File operation handlers (list, read, write, delete, rename, move)
  skill.py       - Skill install/uninstall handlers
  config.py      - Config get/put handlers
  admin.py       - Dispatcher + health/activity/config handlers

Software install/uninstall is handled by specialagent.core.software.SoftwareManagement
(used by admin dispatch and agent loop).
"""

from specialagent.worker.handlers.admin import dispatch

__all__ = ["dispatch"]
