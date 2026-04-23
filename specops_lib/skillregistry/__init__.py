"""SkillRegistry implementations.

:class:`SkillsShRegistry` serves the remote ``agentskill.sh`` catalog.
:class:`YamlSkillRegistry` wraps it with an admin-managed self-hosted YAML
catalog whose entries carry inline ``SKILL.md`` content.
"""

from specops_lib.skillregistry.skills_sh import SkillsShRegistry
from specops_lib.skillregistry.yaml_catalog import YamlSkillRegistry

__all__ = [
    "SkillsShRegistry",
    "YamlSkillRegistry",
]
