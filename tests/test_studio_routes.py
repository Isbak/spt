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
    # The redesigned workbench chrome is present.
    assert "wb-activitybar" in html
    assert "Source Control" in html
    assert "wb-statusbar" in html


def _scaffold(client):
    """Scaffold a small model into the field-service workspace."""
    return client.post(
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
    )


def test_studio_status_reports_changes(client_with_domain):
    _scaffold(client_with_domain)  # scaffold commits, so the tree starts clean
    client_with_domain.post(
        "/api/studio/file",
        json={"domain_id": "field-service", "path": "rdf/data/extra.ttl", "content": "# new\n"},
    )
    body = client_with_domain.get("/api/studio/status?domain_id=field-service").get_json()
    assert body["branch"] == "authoring/field-service"
    paths = {f["path"] for f in body["files"]}
    assert "rdf/data/extra.ttl" in paths


def test_studio_status_unknown_domain_is_empty(client):
    body = client.get("/api/studio/status?domain_id=missing").get_json()
    assert body == {"branch": "", "clean": True, "files": []}


def test_studio_diff_returns_text(client_with_domain):
    _scaffold(client_with_domain)
    # Edit a committed file so there is an uncommitted diff to show.
    client_with_domain.post(
        "/api/studio/file",
        json={
            "domain_id": "field-service",
            "path": "rdf/ontology/ontology.ttl",
            "content": "# edited by test\n",
        },
    )
    body = client_with_domain.get(
        "/api/studio/diff?domain_id=field-service&path=rdf/ontology/ontology.ttl"
    ).get_json()
    assert "edited by test" in body["diff"]


def test_studio_validate_workspace(client_with_domain):
    _scaffold(client_with_domain)
    body = client_with_domain.post(
        "/api/studio/validate", json={"domain_id": "field-service"}
    ).get_json()
    assert body["ok"] is True
    assert body["errors"] == 0
    assert isinstance(body["problems"], list)


def test_studio_validate_unknown_domain(client):
    assert client.post("/api/studio/validate", json={"domain_id": "x"}).status_code == 404


def test_studio_query_workspace(client_with_domain):
    _scaffold(client_with_domain)
    body = client_with_domain.post(
        "/api/studio/query",
        json={"domain_id": "field-service", "query": "SELECT ?s WHERE { ?s a owl:Class } LIMIT 5"},
    ).get_json()
    assert "rows" in body and "columns" in body


def test_studio_query_bad_sparql_returns_error_inline(client_with_domain):
    _scaffold(client_with_domain)
    body = client_with_domain.post(
        "/api/studio/query",
        json={"domain_id": "field-service", "query": "NOT SPARQL"},
    ).get_json()
    assert "error" in body
    assert body["rows"] == []


def test_studio_analytics_workspace(client_with_domain):
    _scaffold(client_with_domain)
    body = client_with_domain.post(
        "/api/studio/analytics", json={"domain_id": "field-service"}
    ).get_json()
    assert "triples" in body
    assert body["class_count"] >= 1


def test_studio_search_workspace(client_with_domain):
    _scaffold(client_with_domain)
    body = client_with_domain.post(
        "/api/studio/search", json={"domain_id": "field-service", "query": "Technician"}
    ).get_json()
    assert "results" in body
    assert isinstance(body["results"], list)


def test_studio_graph_workspace(client_with_domain):
    _scaffold(client_with_domain)
    body = client_with_domain.post(
        "/api/studio/graph", json={"domain_id": "field-service"}
    ).get_json()
    assert "nodes" in body and "edges" in body
    assert body["node_count"] >= 1
    assert all("group" in n and "degree" in n for n in body["nodes"])


def test_studio_graph_node_detail(client_with_domain):
    _scaffold(client_with_domain)
    graph = client_with_domain.post(
        "/api/studio/graph", json={"domain_id": "field-service"}
    ).get_json()
    uri = graph["nodes"][0]["id"]
    detail = client_with_domain.post(
        "/api/studio/graph/node", json={"domain_id": "field-service", "uri": uri}
    ).get_json()
    assert detail["id"] == uri
    assert "outgoing" in detail and "incoming" in detail


def test_studio_graph_node_requires_uri(client_with_domain):
    assert (
        client_with_domain.post(
            "/api/studio/graph/node", json={"domain_id": "field-service"}
        ).status_code
        == 400
    )


def test_studio_graph_unknown_domain(client):
    assert client.post("/api/studio/graph", json={"domain_id": "x"}).status_code == 404
    assert (
        client.post("/api/studio/graph/node", json={"domain_id": "x", "uri": "a"}).status_code
        == 404
    )


def test_studio_analytics_unknown_domain(client):
    assert client.post("/api/studio/analytics", json={"domain_id": "x"}).status_code == 404


def test_studio_query_unknown_domain(client):
    assert client.post("/api/studio/query", json={"domain_id": "x", "query": "SELECT * {}"}).status_code == 404


def test_studio_search_unknown_domain(client):
    assert client.post("/api/studio/search", json={"domain_id": "x", "query": "a"}).status_code == 404


def test_studio_diff_unknown_domain_degrades(client):
    body = client.get("/api/studio/diff?domain_id=x&path=a.ttl").get_json()
    assert body["diff"] == ""
    assert "error" in body


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
