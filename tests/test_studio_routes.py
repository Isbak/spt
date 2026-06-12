"""Tests for the modelling studio routes."""

from __future__ import annotations

import pytest

from app.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    return create_app().test_client()


@pytest.fixture()
def client_with_domain(client):
    client.post("/api/setup/domains", json={"label": "Field Service", "remote_url": ""})
    return client


def test_studio_page_renders_setup_prompt_without_domains(client):
    html = client.get("/studio").get_data(as_text=True)
    assert "Knowledge Modelling Studio" in html
    assert "Domain Repos" in html


def test_studio_page_lists_domains(client_with_domain):
    html = client_with_domain.get("/studio").get_data(as_text=True)
    assert "Field Service" in html
    assert "Quick scaffold" in html


def test_studio_chat_without_domain_prompts_setup(client):
    body = client.post("/api/studio/chat", json={"domain_id": None, "message": "hi"}).get_json()
    assert body["status"] == "needs_domain_setup"


def test_studio_scaffold_writes_and_validates(client_with_domain):
    body = client_with_domain.post(
        "/api/studio/chat",
        json={
            "domain_id": "field-service",
            "answers": {
                "domain_label": "Field Service",
                "prefix": "fs",
                "base_namespace": "https://example.org/fs#",
                "classes": ["Technician", "WorkOrder"],
                "properties": [],
            },
        },
    ).get_json()
    assert body["status"] == "drafted"
    assert body["validation_ok"] is True
    assert "rdf/ontology/ontology.ttl" in body["files"]

    tree = client_with_domain.get("/api/studio/tree?domain_id=field-service").get_json()
    assert "rdf/ontology/ontology.ttl" in tree["files"]

    read = client_with_domain.get("/api/studio/file?domain_id=field-service&path=rdf/ontology/ontology.ttl").get_json()
    assert "owl:Ontology" in read["content"]


def test_studio_write_and_read_roundtrip(client_with_domain):
    saved = client_with_domain.post(
        "/api/studio/file",
        json={"domain_id": "field-service", "path": "rdf/data/extra.ttl", "content": "# edited\n"},
    )
    assert saved.status_code == 200
    read = client_with_domain.get("/api/studio/file?domain_id=field-service&path=rdf/data/extra.ttl").get_json()
    assert read["content"] == "# edited\n"


def test_studio_file_unknown_domain(client):
    assert client.post("/api/studio/file", json={"domain_id": "x", "path": "a.ttl", "content": ""}).status_code == 404


def test_studio_pr_local_only(client_with_domain):
    client_with_domain.post(
        "/api/studio/chat",
        json={"domain_id": "field-service", "answers": {"domain_label": "FS", "classes": ["A"], "properties": []}},
    )
    body = client_with_domain.post("/api/studio/pr", json={"domain_id": "field-service"}).get_json()
    assert body["branch"] == "authoring/field-service"
    assert body["pull_request_url"] is None


def test_studio_pr_unknown_domain(client):
    assert client.post("/api/studio/pr", json={"domain_id": "missing"}).status_code == 404
