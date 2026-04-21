"""Tests for the self-hosted skills feature.

Covers:
- :class:`YamlSkillRegistry` — tagging, query matching, install routing, CRUD.
- Self-hosted catalog merging with the remote ``agentskill.sh`` search results.
"""

from pathlib import Path

import pytest
import yaml

from clawlib.skillregistry import YamlSkillRegistry
from clawlib.skillregistry.skills_sh import SkillsShRegistry


class _StubSkillsShRegistry(SkillsShRegistry):
    """Stub that returns canned search results and records install calls."""

    def __init__(self, results: list[dict] | None = None) -> None:
        self._results = results or []
        self.install_calls: list[tuple[str, Path, dict | None]] = []

    async def search_skills(self, query: str, limit: int) -> list[dict]:
        return list(self._results)[:limit]

    async def install_skill(
        self,
        slug: str,
        dest: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        self.install_calls.append((slug, dest, env))
        return 0, "delegated", ""


def _write_yaml(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")


@pytest.fixture
def sample_custom_entry() -> dict:
    return {
        "slug": "my-pdf-helper",
        "name": "PDF Helper",
        "description": "Internal PDF utilities",
        "author": "Platform Team",
        "version": "1.0.0",
        "categories": ["docs"],
        "homepage": "",
        "repository": "",
        "required_env": [],
        "skill_content": (
            "---\n"
            "name: pdf-helper\n"
            "description: Internal PDF utilities\n"
            "---\n\n"
            "# PDF Helper\n\n"
            "Handles PDFs.\n"
        ),
    }


class TestYamlSkillRegistrySearch:
    @pytest.mark.asyncio
    async def test_search_merges_and_tags_source(self, tmp_path: Path, sample_custom_entry: dict):
        custom_path = tmp_path / "custom_skills.yaml"
        _write_yaml(custom_path, [sample_custom_entry])
        inner = _StubSkillsShRegistry(
            results=[{"slug": "acme/foo@bar", "name": "Foo", "description": "", "downloads": 5}]
        )
        reg = YamlSkillRegistry(custom_catalog_path=custom_path, inner=inner)

        results = await reg.search_skills("", limit=20)

        # Self-hosted entries appear first and are tagged; remote entries also tagged.
        assert results[0]["source"] == "self-hosted"
        assert results[0]["slug"] == "my-pdf-helper"
        # The raw skill_content must not leak to search results — it can be large.
        assert "skill_content" not in results[0]
        assert results[1]["source"] == "agentskill.sh"
        assert results[1]["slug"] == "acme/foo@bar"

    @pytest.mark.asyncio
    async def test_search_filters_custom_by_query(self, tmp_path: Path, sample_custom_entry: dict):
        other = {
            **sample_custom_entry,
            "slug": "other",
            "name": "Other",
            "description": "Spreadsheets",
        }
        custom_path = tmp_path / "custom_skills.yaml"
        _write_yaml(custom_path, [sample_custom_entry, other])
        inner = _StubSkillsShRegistry(results=[])
        reg = YamlSkillRegistry(custom_catalog_path=custom_path, inner=inner)

        results = await reg.search_skills("pdf", limit=20)
        slugs = [r["slug"] for r in results]
        assert "my-pdf-helper" in slugs
        assert "other" not in slugs

    @pytest.mark.asyncio
    async def test_search_survives_remote_failure(self, tmp_path: Path, sample_custom_entry: dict):
        custom_path = tmp_path / "custom_skills.yaml"
        _write_yaml(custom_path, [sample_custom_entry])

        class _BrokenInner(SkillsShRegistry):
            async def search_skills(self, query: str, limit: int) -> list[dict]:
                raise RuntimeError("network down")

            async def install_skill(self, slug: str, dest: Path, env=None):
                return 0, "", ""

        reg = YamlSkillRegistry(custom_catalog_path=custom_path, inner=_BrokenInner())
        results = await reg.search_skills("", limit=20)
        assert [r["slug"] for r in results] == ["my-pdf-helper"]


class TestYamlSkillRegistryInstall:
    @pytest.mark.asyncio
    async def test_install_self_hosted_writes_skill_md(
        self, tmp_path: Path, sample_custom_entry: dict
    ):
        custom_path = tmp_path / "custom_skills.yaml"
        _write_yaml(custom_path, [sample_custom_entry])
        inner = _StubSkillsShRegistry()
        reg = YamlSkillRegistry(custom_catalog_path=custom_path, inner=inner)

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        rc, stdout, stderr = await reg.install_skill("my-pdf-helper", workspace)

        assert rc == 0
        assert stderr == ""
        skill_file = workspace / ".agents" / "skills" / "my-pdf-helper" / "SKILL.md"
        assert skill_file.exists()
        assert skill_file.read_text() == sample_custom_entry["skill_content"]
        assert inner.install_calls == []  # did not delegate

    @pytest.mark.asyncio
    async def test_install_non_custom_delegates_to_inner(self, tmp_path: Path):
        custom_path = tmp_path / "custom_skills.yaml"
        _write_yaml(custom_path, [])
        inner = _StubSkillsShRegistry()
        reg = YamlSkillRegistry(custom_catalog_path=custom_path, inner=inner)

        rc, stdout, stderr = await reg.install_skill("acme/foo@bar", tmp_path)
        assert rc == 0
        assert stdout == "delegated"
        assert len(inner.install_calls) == 1
        assert inner.install_calls[0][0] == "acme/foo@bar"


class TestYamlSkillRegistryCrud:
    def test_add_get_update_delete(self, tmp_path: Path, sample_custom_entry: dict):
        custom_path = tmp_path / "custom_skills.yaml"
        reg = YamlSkillRegistry(custom_catalog_path=custom_path)

        reg.add_custom_entry(sample_custom_entry)
        assert reg.get_entry("my-pdf-helper") is not None
        assert [e["slug"] for e in reg.list_custom_entries()] == ["my-pdf-helper"]

        updated = {**sample_custom_entry, "name": "PDF Helper 2"}
        assert reg.update_custom_entry("my-pdf-helper", updated)
        assert reg.get_entry("my-pdf-helper")["name"] == "PDF Helper 2"

        assert reg.delete_custom_entry("my-pdf-helper") is True
        assert reg.get_entry("my-pdf-helper") is None

    def test_missing_catalog_returns_empty(self, tmp_path: Path):
        reg = YamlSkillRegistry(custom_catalog_path=tmp_path / "nope.yaml")
        assert reg.list_custom_entries() == []
        assert reg.get_entry("anything") is None

    def test_update_missing_returns_false(self, tmp_path: Path):
        custom_path = tmp_path / "custom_skills.yaml"
        _write_yaml(custom_path, [])
        reg = YamlSkillRegistry(custom_catalog_path=custom_path)
        assert reg.update_custom_entry("nope", {"slug": "nope", "name": "N"}) is False
        assert reg.delete_custom_entry("nope") is False

    def test_add_without_custom_path_raises(self):
        reg = YamlSkillRegistry(custom_catalog_path=None)
        with pytest.raises(RuntimeError):
            reg.add_custom_entry({"slug": "x", "name": "X"})
