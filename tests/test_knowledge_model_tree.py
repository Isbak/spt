"""Tests for the Knowledge Model context tree mounted under /model/<domain_id>/."""

from __future__ import annotations

import pytest

from app.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    return create_app().test_client()


@pytest.fixture()
def scaffolded_client(client):
    """Register and scaffold a domain so its rdf/ tree exists."""
    client.post("/api/setup/domains", json={"label": "Field Service", "remote_url": ""})
    client.post(
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
    return client


def test_km_ontology_renders_domain_model(scaffolded_client):
    html = scaffolded_client.get("/model/field-service/ontology").get_data(as_text=True)
    assert "fs#" in html or "Field Service" in html


@pytest.mark.parametrize(
    "path",
    [
        "/model/field-service/ontology",
        "/model/field-service/graphs",
        "/model/field-service/domain-models",
        "/model/field-service/shapes",
        "/model/field-service/governance",
        "/model/field-service/named-graphs",
        "/model/field-service/ontology-version",
        "/model/field-service/query",
        "/model/field-service/provenance",
        "/model/field-service/reasoning",
        "/model/field-service/consistency",
        "/model/field-service/rules",
        "/model/field-service/graph",
        "/model/field-service/ontology-browser",
        "/model/field-service/governance-dashboard",
        "/model/field-service/analytics",
        "/model/field-service/search?q=Technician",
    ],
)
def test_km_angle_views_render(scaffolded_client, path):
    assert scaffolded_client.get(path).status_code == 200


def test_km_unknown_domain_returns_404(client):
    assert client.get("/model/missing/ontology").status_code == 404


def test_km_switcher_offers_system_and_domain(scaffolded_client):
    html = scaffolded_client.get("/model/field-service/ontology").get_data(as_text=True)
    assert "context-switcher" in html
    assert "/ontology" in html  # link back to the System tree
    assert "Field Service" in html


def test_system_tree_unaffected(scaffolded_client):
    # The System tree keeps its original URLs and renders the platform self-model.
    assert scaffolded_client.get("/ontology").status_code == 200
    assert scaffolded_client.get("/graphs").status_code == 200
