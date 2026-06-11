"""Live external-integration tests against REAL services (no simulator).

These mirror the agent LLM assist's real-model tests: each one **follows the
chosen option** — it activates when its external service is configured/reachable
and skips cleanly otherwise (hermetic CI has neither). The two services are
independent, so e.g. a self-contained warehouse with an external Jena runs only
the Jena test.

Bring services up and select them, then run normally — no extra flag:

    # External warehouse backing the example mappings (seeded postgres):
    make docker-up   # then start postgres: docker compose --profile integration up -d
    SOURCE_DATABASE_URL=postgresql+psycopg://semantic:semantic@localhost:5432/semantic_platform \
        python -m pytest tests/test_external_integration_live.py

    # Real Jena (the bundled Fuseki counts) — just have it running:
    make docker-up && make load-fuseki
    python -m pytest tests/test_external_integration_live.py

Real-service output is asserted on robust properties, not fixed values.
"""

from __future__ import annotations

import dataclasses

import pytest
from rdflib import Graph

from semantic_platform.api import fuseki_graph_triple_counts
from semantic_platform.config import load_settings
from semantic_platform.fuseki import FusekiClient
from semantic_platform.materialize import materialize_mappings, resolve_row_source


def _warehouse_ready() -> bool:
    """True when an external warehouse is the chosen source and backs the mappings."""
    settings = load_settings()
    if not settings.source_database_url:  # external warehouse is the chosen option
        return False
    try:
        source = resolve_row_source(settings)
        try:
            source.fetch("SELECT 1 FROM dataset LIMIT 1")  # mappings' table present?
            return True
        finally:
            source.close()
    except Exception:
        return False


def _jena_ready() -> bool:
    """True when a real Fuseki/Jena (bundled or external) is reachable."""
    try:
        client = FusekiClient()
        return client.health_check().ok and client.dataset_exists()
    except Exception:
        return False


@pytest.mark.skipif(
    not _warehouse_ready(),
    reason="Set SOURCE_DATABASE_URL to a DB backing the example mappings (e.g. the seeded postgres).",
)
def test_live_warehouse_materializes(tmp_path):
    settings = dataclasses.replace(load_settings(), output_dir=tmp_path / "out")
    results = materialize_mappings(settings)
    assert results and all(result.triple_count > 0 for result in results)
    for result in results:
        graph = Graph()
        graph.parse(result.output_path, format="turtle")
        assert len(graph) > 0


@pytest.mark.skipif(
    not _jena_ready(),
    reason="Start a Fuseki (make docker-up) or point FUSEKI_BASE_URL at a reachable Jena.",
)
def test_live_jena_round_trip(tmp_path):
    client = FusekiClient()
    graph_uri = "urn:graph:live-e2e"
    ttl = tmp_path / "graph.ttl"
    ttl.write_text(
        "@prefix ex: <https://example.org/> . ex:s ex:p ex:o . ex:s ex:q ex:r .",
        encoding="utf-8",
    )
    client.upload_graph(ttl, graph_uri)
    counts = fuseki_graph_triple_counts([graph_uri])
    assert counts.get(graph_uri, 0) >= 2
