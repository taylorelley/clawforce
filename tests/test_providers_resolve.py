"""Tests for resolve_provider_ref: looks up an admin-managed provider row and
materialises credentials into the config dict sent to the agent worker.
"""

from pathlib import Path

import pytest

from specops.core.database import Database
from specops.core.providers_resolve import resolve_provider_ref
from specops.core.store.llm_providers import LLMProviderStore


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def store(db: Database) -> LLMProviderStore:
    return LLMProviderStore(db, fernet=None)


class TestResolveProviderRef:
    def test_noop_when_no_providers(self, store: LLMProviderStore):
        cfg = {"agents": {"defaults": {"model": "x"}}}
        assert resolve_provider_ref(cfg, store) == cfg

    def test_noop_when_provider_ref_missing(self, store: LLMProviderStore):
        cfg = {"providers": {"openai": {"api_key": "direct"}}}
        assert resolve_provider_ref(cfg, store) == cfg

    def test_resolves_openai_provider(self, store: LLMProviderStore):
        row = store.create(
            name="OpenAI-prod",
            type="openai",
            api_key="sk-resolved-key",
            api_base="",
        )
        cfg = {"providers": {"provider_ref": row["id"]}}
        resolved = resolve_provider_ref(cfg, store)
        assert resolved["providers"]["openai"]["api_key"] == "sk-resolved-key"
        # provider_ref is kept so the UI round-trips the selection
        assert resolved["providers"]["provider_ref"] == row["id"]

    def test_resolves_with_api_base(self, store: LLMProviderStore):
        row = store.create(
            name="Custom-gateway",
            type="custom",
            api_key="key",
            api_base="https://example.com/v1",
        )
        cfg = {"providers": {"provider_ref": row["id"]}}
        resolved = resolve_provider_ref(cfg, store)
        assert resolved["providers"]["custom"]["api_key"] == "key"
        assert resolved["providers"]["custom"]["api_base"] == "https://example.com/v1"

    def test_merges_with_existing_slot(self, store: LLMProviderStore):
        row = store.create(name="A", type="anthropic", api_key="sk-new")
        cfg = {
            "providers": {
                "provider_ref": row["id"],
                # Existing slot from prior config should merge, with resolved keys winning.
                "anthropic": {"extra_headers": {"X": "Y"}, "api_key": "stale"},
            }
        }
        resolved = resolve_provider_ref(cfg, store)
        assert resolved["providers"]["anthropic"]["api_key"] == "sk-new"
        assert resolved["providers"]["anthropic"]["extra_headers"] == {"X": "Y"}

    def test_unknown_ref_is_noop(self, store: LLMProviderStore):
        cfg = {"providers": {"provider_ref": "does-not-exist"}}
        assert resolve_provider_ref(cfg, store) == cfg

    def test_oauth_slot_left_untouched(self, store: LLMProviderStore):
        row = store.create(name="A", type="openai", api_key="sk")
        cfg = {
            "providers": {
                "provider_ref": row["id"],
                "chatgpt": {"api_key": "oauth-token-json"},
            }
        }
        resolved = resolve_provider_ref(cfg, store)
        # OAuth provider slot must remain
        assert resolved["providers"]["chatgpt"] == {"api_key": "oauth-token-json"}
        assert resolved["providers"]["openai"]["api_key"] == "sk"

    def test_camelcase_provider_ref_alias(self, store: LLMProviderStore):
        row = store.create(name="A", type="openai", api_key="sk-alias")
        cfg = {"providers": {"providerRef": row["id"]}}
        resolved = resolve_provider_ref(cfg, store)
        assert resolved["providers"]["openai"]["api_key"] == "sk-alias"

    def test_returns_new_dict_not_mutating_input(self, store: LLMProviderStore):
        row = store.create(name="A", type="openai", api_key="sk")
        cfg = {"providers": {"provider_ref": row["id"]}}
        resolved = resolve_provider_ref(cfg, store)
        # input dict should not gain the resolved slot
        assert "openai" not in cfg["providers"]
        assert "openai" in resolved["providers"]
