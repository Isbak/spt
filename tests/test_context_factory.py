"""Tests for the domain data-context Settings factory (ADR-0018)."""

from __future__ import annotations

import pytest

from semantic_platform.authoring import workspace_config as wc
from semantic_platform.config import load_settings
from semantic_platform.context import domain_settings
from semantic_platform.graph import load_graph


@pytest.fixture()
def configured_domain(tmp_path, monkeypatch):
    """Register a domain backed by a fresh local repo and return its id."""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    wc.add_domain(label="Field Service", remote_url="")
    return "field-service"


def test_domain_settings_repoints_rdf_dirs(configured_domain):
    base = load_settings()
    ds = domain_settings(configured_domain)
    expected_root = base.workspace_root / "domains" / configured_domain / "rdf"

    assert ds.rdf_root == expected_root
    assert ds.ontology_dir == expected_root / "ontology"
    assert ds.shapes_dir == expected_root / "shapes"
    assert ds.data_dir == expected_root / "data"
    assert ds.queries_dir == expected_root / "queries"
    # Non-RDF fields are untouched: a KM context only re-points the rdf/ tree.
    assert ds.workspace_root == base.workspace_root
    assert ds.fuseki_system == base.fuseki_system


def test_domain_settings_unknown_domain_raises(configured_domain):
    with pytest.raises(KeyError):
        domain_settings("does-not-exist")


def test_domain_settings_empty_repo_loads_empty_graph(configured_domain):
    """An unscaffolded domain (no rdf/ subdirs) renders empty, not an error."""
    ds = domain_settings(configured_domain)
    graph = load_graph(settings=ds)
    assert len(graph) == 0
