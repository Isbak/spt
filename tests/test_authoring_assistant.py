"""Tests for the governed authoring conversation engine and auto provider."""

from __future__ import annotations

import dataclasses
import subprocess

import pytest

from semantic_platform.agents import llm
from semantic_platform.agents.llm import (
    AnthropicModel,
    LocalDeterministicModel,
    OllamaModel,
    resolve_language_model,
)
from semantic_platform.authoring import workspace_config as wc
from semantic_platform.authoring.assistant import (
    STATUS_DRAFTED,
    STATUS_NEEDS_DOMAIN,
    STATUS_QUESTION,
    author_model,
    chat_turn,
    open_pr,
)
from semantic_platform.authoring.scaffold import InterviewAnswers
from semantic_platform.config import load_settings


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    return load_settings()


# --- auto provider resolution ------------------------------------------------


def test_auto_prefers_anthropic_then_ollama_then_local(monkeypatch):
    base = dataclasses.replace(load_settings(), llm_provider="auto")
    monkeypatch.setattr(llm, "anthropic_configured", lambda: True)
    assert isinstance(resolve_language_model(base), AnthropicModel)

    monkeypatch.setattr(llm, "anthropic_configured", lambda: False)
    monkeypatch.setattr(llm, "ollama_reachable", lambda: True)
    assert isinstance(resolve_language_model(base), OllamaModel)

    monkeypatch.setattr(llm, "ollama_reachable", lambda: False)
    assert isinstance(resolve_language_model(base), LocalDeterministicModel)


# --- needs-domain-setup guard ------------------------------------------------


def test_chat_without_domain_prompts_setup(settings):
    result = chat_turn(None, "help me model", settings=settings)
    assert result.status == STATUS_NEEDS_DOMAIN
    assert "Domain Repos" in result.reply

    missing = author_model("nope", InterviewAnswers(domain_label="X"), settings=settings)
    assert missing.status == STATUS_NEEDS_DOMAIN


# --- conversation and authoring ---------------------------------------------


def test_chat_turn_asks_a_question(settings):
    wc.add_domain("Field Service", "", settings=settings)
    result = chat_turn("field-service", "I want to model dispatch", settings=settings)
    assert result.status == STATUS_QUESTION
    assert result.provider == "local"
    assert result.reply


def test_author_model_writes_validates_and_commits(settings):
    wc.add_domain("Field Service", "", settings=settings)
    answers = InterviewAnswers(
        domain_label="Field Service",
        prefix="fs",
        base_namespace="https://example.org/fs#",
        classes=("Technician", "WorkOrder"),
    )
    result = author_model("field-service", answers, settings=settings)
    assert result.status == STATUS_DRAFTED
    assert result.validation_ok is True
    assert result.branch == "authoring/field-service"
    assert "rdf/ontology/ontology.ttl" in result.files
    assert result.provenance is not None and len(result.provenance) > 0


def test_open_pr_without_remote_is_local_only(settings):
    wc.add_domain("Field Service", "", settings=settings)
    author_model("field-service", InterviewAnswers(domain_label="FS", classes=("A",)), settings=settings)
    ref = open_pr("field-service", settings=settings)
    assert ref.pull_request_url is None
    assert ref.pushed is False

    with pytest.raises(KeyError):
        open_pr("missing", settings=settings)


def test_open_pr_reports_successful_push_to_non_github_remote(settings, tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    wc.add_domain("Field Service", origin.as_uri(), settings=settings)
    author_model("field-service", InterviewAnswers(domain_label="FS", classes=("A",)), settings=settings)

    ref = open_pr("field-service", settings=settings)
    # Push genuinely succeeded to the file:// remote, so it must not be reported local-only.
    assert ref.pushed is True
    assert "pushed" in ref.message.lower()
    refs = subprocess.run(
        ["git", "ls-remote", str(origin), "refs/heads/authoring/field-service"],
        capture_output=True, text=True,
    ).stdout
    assert "authoring/field-service" in refs
