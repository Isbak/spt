"""Tests for per-role storage bundles and backward-compatible config aliases (ADR-0017)."""

from __future__ import annotations

import pytest

from semantic_platform.config import FusekiDataset, SourceDatabase, load_settings


@pytest.fixture(autouse=True)
def _clear_storage_env(monkeypatch):
    """Start each test from a clean slate for storage-related env vars."""
    for name in (
        "FUSEKI_BASE_URL", "FUSEKI_DATASET", "FUSEKI_USERNAME", "FUSEKI_PASSWORD",
        "FUSEKI_ADMIN_PASSWORD",
        "FUSEKI_SYSTEM_BASE_URL", "FUSEKI_SYSTEM_DATASET",
        "FUSEKI_AGENTS_BASE_URL", "FUSEKI_AGENTS_DATASET",
        "FUSEKI_AGENTS_USERNAME", "FUSEKI_AGENTS_PASSWORD",
        "FUSEKI_BUSINESS_BASE_URL", "FUSEKI_BUSINESS_DATASET",
        "FUSEKI_BUSINESS_USERNAME", "FUSEKI_BUSINESS_PASSWORD",
        "SOURCE_DATABASE_URL", "SOURCE_BUSINESS_DATABASE_URL", "SOURCE_AGENTS_DATABASE_URL",
        "MATERIALIZE_SQL_FILES", "MATERIALIZE_BUSINESS_SQL_FILES", "MATERIALIZE_AGENTS_SQL_FILES",
        "MAPPINGS_SQL_DIR", "MAPPINGS_BUSINESS_SQL_DIR", "MAPPINGS_AGENTS_SQL_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_bundles_are_distinct_datasets():
    settings = load_settings()
    assert isinstance(settings.fuseki_system, FusekiDataset)
    assert settings.fuseki_system.dataset == "semantic-platform"
    assert settings.fuseki_agents.dataset == "semantic-platform-agents"
    assert settings.fuseki_business.dataset == "semantic-platform-business"
    # All co-located on the same base URL by default (single local Fuseki).
    base = settings.fuseki_system.base_url
    assert settings.fuseki_agents.base_url == base
    assert settings.fuseki_business.base_url == base


def test_role_specific_base_url_places_business_remotely(monkeypatch):
    monkeypatch.setenv("FUSEKI_BASE_URL", "http://local:3030")
    monkeypatch.setenv("FUSEKI_BUSINESS_BASE_URL", "https://remote:3030")
    settings = load_settings()
    assert settings.fuseki_system.base_url == "http://local:3030"
    assert settings.fuseki_agents.base_url == "http://local:3030"
    assert settings.fuseki_business.base_url == "https://remote:3030"
    assert settings.fuseki_business.dataset_url == "https://remote:3030/semantic-platform-business"


def test_fuseki_helper_and_aliases_resolve_to_system(monkeypatch):
    monkeypatch.setenv("FUSEKI_BASE_URL", "http://host:3030")
    monkeypatch.setenv("FUSEKI_DATASET", "legacy-name")
    settings = load_settings()
    assert settings.fuseki("system") is settings.fuseki_system
    # Legacy flat aliases delegate to the system bundle.
    assert settings.fuseki_base_url == "http://host:3030"
    assert settings.fuseki_dataset == "legacy-name"
    assert settings.fuseki_dataset_url == "http://host:3030/legacy-name"
    assert settings.fuseki_query_url.endswith("/legacy-name/query")
    assert settings.fuseki_data_url.endswith("/legacy-name/data")


def test_unknown_fuseki_role_raises():
    with pytest.raises(ValueError):
        load_settings().fuseki("nope")


def test_credentials_default_username_to_admin_and_inherit(monkeypatch):
    monkeypatch.setenv("FUSEKI_ADMIN_PASSWORD", "secret")
    settings = load_settings()
    # A lone password defaults the username to admin, for every role.
    assert settings.fuseki_system.username == "admin"
    assert settings.fuseki_agents.username == "admin"
    assert (settings.fuseki_agents.username, settings.fuseki_agents.password) == ("admin", "secret")


def test_role_credentials_override_shared(monkeypatch):
    monkeypatch.setenv("FUSEKI_PASSWORD", "shared")
    monkeypatch.setenv("FUSEKI_BUSINESS_PASSWORD", "biz")
    monkeypatch.setenv("FUSEKI_BUSINESS_USERNAME", "bizuser")
    settings = load_settings()
    assert (settings.fuseki_business.username, settings.fuseki_business.password) == ("bizuser", "biz")
    assert settings.fuseki_system.password == "shared"


def test_source_bundles_for_business_and_agents_not_system():
    settings = load_settings()
    assert isinstance(settings.source_business, SourceDatabase)
    assert isinstance(settings.source("agents"), SourceDatabase)
    with pytest.raises(ValueError):
        settings.source("system")


def test_source_url_role_override_and_shared_fallback(monkeypatch):
    monkeypatch.setenv("SOURCE_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("SOURCE_BUSINESS_DATABASE_URL", "postgresql://b/db")
    settings = load_settings()
    # Business uses its own URL; agents inherits the shared one.
    assert settings.source_business.database_url == "postgresql://b/db"
    assert settings.source_agents.database_url == "sqlite://"
    # Legacy alias points at the business bundle.
    assert settings.source_database_url == "postgresql://b/db"


def test_source_sql_dir_falls_back_to_shared(monkeypatch, tmp_path):
    monkeypatch.setenv("MAPPINGS_SQL_DIR", str(tmp_path / "shared"))
    monkeypatch.setenv("MAPPINGS_AGENTS_SQL_DIR", str(tmp_path / "agents"))
    settings = load_settings()
    assert settings.source_business.sql_dir == (tmp_path / "shared").resolve()
    assert settings.source_agents.sql_dir == (tmp_path / "agents").resolve()
    # Legacy alias mirrors business.
    assert settings.sql_dir == settings.source_business.sql_dir
