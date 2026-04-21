"""SkillRegistry implementation that merges agentskill.sh results with self-hosted entries.

Self-hosted skills are admin-managed entries stored in a YAML catalog. Each entry
carries the full ``SKILL.md`` content; installing a self-hosted skill writes that
content directly into ``<workspace>/.agents/skills/<slug>/SKILL.md`` — bypassing
``npx skills``.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from clawlib.skillregistry.skills_sh import SkillsShRegistry

logger = logging.getLogger(__name__)


def _load_yaml_list(path: Path) -> list[dict[str, Any]]:
    """Load a YAML file expected to contain a list of dicts. Returns [] on any error."""
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, list):
            logger.warning("Custom skills catalog at %s is not a list", path)
            return []
        return data
    except (yaml.YAMLError, OSError) as e:
        logger.warning("Failed to load custom skills catalog at %s: %s", path, e)
        return []


def _atomic_write_yaml(path: Path, data: list[dict[str, Any]]) -> None:
    """Write YAML atomically via a temp file in the same directory, fsync, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.dump(data, allow_unicode=True, sort_keys=False)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Shape a self-hosted catalog entry to match the MarketplaceSkill search response."""
    slug = entry.get("slug", "")
    return {
        "slug": slug,
        "name": entry.get("name", slug),
        "description": entry.get("description", ""),
        "version": entry.get("version", ""),
        "author": entry.get("author", ""),
        "downloads": 0,
        "categories": entry.get("categories") or [],
        "license": entry.get("license", ""),
        "homepage": entry.get("homepage", ""),
        "repository": entry.get("repository", ""),
        "required_env": entry.get("required_env") or [],
        "source": "self-hosted",
    }


def _matches_query(entry: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    needle = query.lower()
    haystack_parts = [
        str(entry.get("name", "")),
        str(entry.get("description", "")),
        str(entry.get("author", "")),
        str(entry.get("slug", "")),
    ]
    haystack_parts.extend(str(c) for c in (entry.get("categories") or []))
    return any(needle in part.lower() for part in haystack_parts)


def _write_skill_md(dest: Path, slug: str, skill_content: str) -> None:
    """Write the stored SKILL.md content into dest/.agents/skills/<slug>/SKILL.md."""
    skill_dir = dest / ".agents" / "skills" / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")


class YamlSkillRegistry:
    """SkillRegistry that wraps :class:`SkillsShRegistry` and merges a self-hosted YAML catalog.

    Self-hosted entries are surfaced in :meth:`search_skills` tagged with
    ``source="self-hosted"``; ``agentskill.sh`` results are tagged
    ``source="agentskill.sh"``. :meth:`install_skill` routes self-hosted slugs
    to a direct file write and delegates everything else to the inner registry.
    """

    def __init__(
        self,
        custom_catalog_path: Path | None = None,
        inner: SkillsShRegistry | None = None,
    ) -> None:
        self._custom_catalog_path = custom_catalog_path
        self._inner = inner or SkillsShRegistry()

    # -- Search ---------------------------------------------------------------

    async def search_skills(self, query: str, limit: int) -> list[dict]:
        """Merge self-hosted entries into the agentskill.sh search results.

        Self-hosted entries that match ``query`` are listed first (followed by
        remote results), each tagged with a ``source`` field. ``limit`` applies
        to the combined result count.
        """
        query = (query or "").strip()
        custom = self.list_custom_entries()
        custom_matches = [_public_entry(entry) for entry in custom if _matches_query(entry, query)]

        remaining = max(0, limit - len(custom_matches))
        remote: list[dict] = []
        if remaining > 0:
            try:
                remote = await self._inner.search_skills(query, remaining)
            except Exception:
                logger.exception("agentskill.sh search failed; returning self-hosted only")
                remote = []
            for entry in remote:
                entry["source"] = "agentskill.sh"

        return [*custom_matches, *remote][:limit]

    # -- Install --------------------------------------------------------------

    async def install_skill(
        self,
        slug: str,
        dest: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """Install a self-hosted or remote skill into ``dest``.

        Self-hosted slugs are resolved against the custom catalog and the stored
        ``SKILL.md`` content is written directly to
        ``dest/.agents/skills/<slug>/SKILL.md``. Anything else is delegated to
        the inner :class:`SkillsShRegistry`.
        """
        entry = self.get_entry(slug)
        if entry and entry.get("skill_content"):
            try:
                _write_skill_md(Path(dest), entry["slug"], entry["skill_content"])
            except OSError as e:
                return 1, "", f"Failed to write SKILL.md: {e}"
            return 0, f"Installed self-hosted skill '{entry['slug']}'", ""
        return await self._inner.install_skill(slug, dest, env)

    # -- Custom CRUD ----------------------------------------------------------

    def list_custom_entries(self) -> list[dict[str, Any]]:
        """Return raw self-hosted catalog entries (including stored ``skill_content``)."""
        if not self._custom_catalog_path:
            return []
        return _load_yaml_list(self._custom_catalog_path)

    def get_entry(self, slug: str) -> dict[str, Any] | None:
        """Return a self-hosted catalog entry by slug, or None if not found."""
        for entry in self.list_custom_entries():
            if entry.get("slug") == slug:
                return entry
        return None

    def add_custom_entry(self, entry: dict[str, Any]) -> None:
        """Append a new entry to the custom catalog YAML file."""
        if not self._custom_catalog_path:
            raise RuntimeError("No custom catalog path configured")
        existing = _load_yaml_list(self._custom_catalog_path)
        existing.append(entry)
        _atomic_write_yaml(self._custom_catalog_path, existing)

    def update_custom_entry(self, slug: str, entry: dict[str, Any]) -> bool:
        """Update an existing custom entry by slug. Returns True if found and updated."""
        if not self._custom_catalog_path:
            return False
        existing = _load_yaml_list(self._custom_catalog_path)
        for i, e in enumerate(existing):
            if e.get("slug") == slug:
                existing[i] = {**e, **entry, "slug": slug}
                _atomic_write_yaml(self._custom_catalog_path, existing)
                return True
        return False

    def delete_custom_entry(self, slug: str) -> bool:
        """Remove a custom entry by slug. Returns True if it was found and removed."""
        if not self._custom_catalog_path:
            return False
        existing = _load_yaml_list(self._custom_catalog_path)
        filtered = [e for e in existing if e.get("slug") != slug]
        if len(filtered) == len(existing):
            return False
        _atomic_write_yaml(self._custom_catalog_path, filtered)
        return True
