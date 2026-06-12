"""Tests for the global, context-aware chat panel."""

from __future__ import annotations

import pytest

from app.app import create_app
from app.page_context import DEFAULT_SCOPE, resolve_page_context


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    return create_app().test_client()


def test_page_context_resolution():
    assert resolve_page_context("governance.index")["scope"] == "governance"
    assert resolve_page_context("ontology.index")["scope"] == "ontology"
    assert resolve_page_context("reasoning.reasoning_index")["scope"] == "reasoning"
    assert resolve_page_context("visualization.governance_dashboard")["scope"] == "governance"
    assert resolve_page_context("visualization.provenance_explorer")["scope"] == "provenance"
    assert resolve_page_context(None)["scope"] == DEFAULT_SCOPE


def test_chat_drawer_renders_on_every_page(client):
    for url in ("/", "/governance", "/reasoning"):
        html = client.get(url).get_data(as_text=True)
        assert 'id="chat-panel"' in html
        assert 'name="chat-context"' in html


def test_ask_mode_returns_scoped_explanation(client):
    response = client.post("/api/chat", json={"message": "summarize", "mode": "ask", "context": {"scope": "reference"}})
    assert response.status_code == 200
    body = response.get_json()
    assert body["mode"] == "ask"
    assert body["scope"] == "reference"
    assert body["reply"]


def test_ask_mode_denied_scope_returns_403(client):
    response = client.post("/api/chat", json={"message": "x", "mode": "ask", "context": {"scope": "transactional"}})
    assert response.status_code == 403
    assert "error" in response.get_json()


def test_empty_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": "  "}).status_code == 400


def test_model_mode_without_domain_prompts_setup(client):
    response = client.post("/api/chat", json={"message": "model it", "mode": "model", "domain_id": None})
    assert response.status_code == 200
    assert response.get_json()["status"] == "needs_domain_setup"


def test_chat_domains_endpoint(client):
    client.post("/api/setup/domains", json={"label": "Field Service", "remote_url": ""})
    items = client.get("/api/chat/domains").get_json()
    assert any(item["id"] == "field-service" for item in items)
