"""Tests for the model setup and domain settings routes."""

from __future__ import annotations

import pytest

from app.app import create_app
from semantic_platform.authoring import workspace_config as wc
from semantic_platform.config import load_settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    return create_app().test_client()


def test_model_setup_page_renders(client):
    html = client.get("/setup/models").get_data(as_text=True)
    assert "Model Setup" in html
    assert "Provider status" in html


def test_set_model_persists(client):
    response = client.post("/api/setup/models", json={"provider": "auto", "model": "claude-opus-4-8"})
    assert response.status_code == 200
    assert wc.get_model_config(load_settings()).provider == "auto"


def test_set_model_rejects_unknown(client):
    assert client.post("/api/setup/models", json={"provider": "bogus"}).status_code == 400


def test_test_connection_uses_offline_local(client):
    body = client.post("/api/setup/models/test").get_json()
    assert body["ok"] is True
    assert body["provider"] == "local"


def test_domain_crud_via_routes(client):
    assert "Domain Repositories" in client.get("/setup/domains").get_data(as_text=True)

    created = client.post("/api/setup/domains", json={"label": "Field Service", "remote_url": "https://github.com/o/r.git"})
    assert created.status_code == 200
    assert created.get_json()["domain_id"] == "field-service"

    assert client.post("/api/setup/domains", json={"label": ""}).status_code == 400

    removed = client.post("/api/setup/domains/field-service/delete", json={})
    assert removed.get_json()["removed"] is True


def test_form_post_redirects(client):
    response = client.post("/api/setup/domains", data={"label": "Form Domain", "remote_url": ""})
    assert response.status_code == 302
