"""WorkerContext: single object carrying all worker runtime components."""

from dataclasses import dataclass
from pathlib import Path

from specialagent.agent.agent_fs import AgentFS
from specialagent.agent.loop import AgentLoop
from specialagent.core.config.engine import ConfigEngine
from specialagent.core.config.schema import Config
from specialagent.core.cron import CronService
from specialagent.core.heartbeat import HeartbeatService
from specialagent.core.software import SoftwareManagement
from specops_lib.activity import ActivityLog
from specops_lib.channels.manager import ChannelManager
from specops_lib.observability import DefenseClawAuditForwarder


@dataclass(slots=True)
class WorkerContext:
    """Immutable bundle for one agent instance (data-plane runtime; one worker = one agent).

    config is always sanitized (secret values replaced by placeholder) so the
    agent and any agent-visible code never see real credentials.
    engine is long-lived so get_config/put_config use it directly (no disk re-read).
    admin_url and agent_token are for the admin WebSocket client only (not in config).
    """

    agent_id: str
    agent_root: Path
    config_path: Path
    config: Config
    engine: ConfigEngine
    agent_loop: AgentLoop
    channels: ChannelManager
    activity_log: ActivityLog
    heartbeat: HeartbeatService
    cron: CronService
    file_service: AgentFS
    software_management: SoftwareManagement
    admin_url: str = ""
    agent_token: str = ""
    audit_forwarder: DefenseClawAuditForwarder | None = None
