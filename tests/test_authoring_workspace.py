"""Tests for the writable workspace configuration (model + domain registry)."""

from __future__ import annotations

import pytest

from semantic_platform.authoring import workspace_config as wc
from semantic_platform.config import load_settings


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    return load_settings()


def test_model_config_defaults_then_persists(settings):
    assert wc.get_model_config(settings).provider == "local"
    config = wc.set_model_config("auto", "claude-opus-4-8", settings=settings)
    assert config.provider == "auto"
    assert config.model == "claude-opus-4-8"
    # Reload via a fresh settings object: the choice survives without env vars.
    reloaded = load_settings()
    assert reloaded.llm_provider == "auto"
    assert reloaded.llm_model == "claude-opus-4-8"


def test_env_wins_over_persisted_model(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    wc.set_model_config("ollama", settings=load_settings())
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert load_settings().llm_provider == "anthropic"  # env overlays above persisted


def test_set_model_config_rejects_unknown_provider(settings):
    with pytest.raises(ValueError):
        wc.set_model_config("definitely-not-a-provider", settings=settings)


def test_domain_registry_add_list_get_remove(settings):
    assert wc.list_domains(settings) == []
    domain = wc.add_domain("Field Service Dispatch", "https://github.com/o/r.git", "develop", "TOK", settings=settings)
    assert domain.domain_id == "field-service-dispatch"
    assert domain.branch == "develop"
    assert domain.token_env == "TOK"
    assert str(settings.workspace_root) in domain.local_path

    assert [d.domain_id for d in wc.list_domains(settings)] == ["field-service-dispatch"]
    assert wc.get_domain("field-service-dispatch", settings).label == "Field Service Dispatch"
    assert wc.get_domain("missing", settings) is None

    # Re-adding the same id updates rather than duplicates.
    wc.add_domain("Field Service Dispatch", "https://github.com/o/r2.git", settings=settings)
    domains = wc.list_domains(settings)
    assert len(domains) == 1
    assert domains[0].remote_url.endswith("r2.git")

    assert wc.remove_domain("field-service-dispatch", settings) is True
    assert wc.remove_domain("field-service-dispatch", settings) is False
    assert wc.list_domains(settings) == []


def test_slugify_handles_messy_labels():
    assert wc.slugify("  Hello, World!! ") == "hello-world"
    assert wc.slugify("***") == "domain"
