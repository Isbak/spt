"""Application service facade used by Flask routes and scripts."""

from __future__ import annotations

from typing import Any

from semantic_platform.config import Settings, load_settings
from semantic_platform.fuseki import FusekiClient, FusekiStatus
from semantic_platform.graph import GraphStats, graph_stats, load_graph
from semantic_platform.materialize import (
    FusekiLoadResult,
    MaterializationResult,
    materialize_mappings,
    push_to_fuseki,
)
from semantic_platform.query import execute_query, read_query, result_rows
from semantic_platform.validate import ShaclValidationReport, SyntaxValidationResult, run_validation


def get_graph_stats(settings: Settings | None = None) -> GraphStats:
    """Load configured RDF assets and return basic statistics."""
    return graph_stats(load_graph(settings=settings or load_settings()))


def get_ontology_text(settings: Settings | None = None) -> str:
    """Return concatenated ontology Turtle for the simple UI."""
    settings = settings or load_settings()
    chunks = []
    for path in sorted(settings.ontology_dir.glob("*.ttl")):
        chunks.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def run_local_query(query_text: str | None = None, settings: Settings | None = None) -> list[dict[str, Any]]:
    """Run a SPARQL query against local RDF assets."""
    settings = settings or load_settings()
    query_text = query_text or read_query(settings.default_query_file)
    return result_rows(execute_query(query_text, load_graph(settings=settings)))


def validate_platform(settings: Settings | None = None) -> tuple[list[SyntaxValidationResult], ShaclValidationReport]:
    """Run all local validation checks."""
    return run_validation(settings=settings or load_settings())


def fuseki_health(settings: Settings | None = None) -> FusekiStatus:
    """Return Fuseki health status."""
    return FusekiClient(settings=settings or load_settings()).health_check()


def upload_default_graphs(settings: Settings | None = None) -> None:
    """Upload ontology, vocabulary and data assets to named graphs."""
    settings = settings or load_settings()
    client = FusekiClient(settings=settings)
    graph_map = {
        settings.ontology_dir / "core.ttl": "urn:semantic-platform:graph:ontology",
        settings.vocabularies_dir / "example-skos.ttl": "urn:semantic-platform:graph:reference",
        settings.data_dir / "example-data.ttl": "urn:semantic-platform:graph:data",
    }
    for path, graph_uri in graph_map.items():
        if path.exists():
            client.upload_graph(path, graph_uri)


def materialize_sources(settings: Settings | None = None) -> list[MaterializationResult]:
    """Materialize all R2RML mappings against the configured relational source."""
    return materialize_mappings(settings=settings or load_settings())


def load_sources_into_fuseki(settings: Settings | None = None) -> list[FusekiLoadResult]:
    """Materialize mappings and push the resulting graphs into Fuseki."""
    settings = settings or load_settings()
    return push_to_fuseki(materialize_mappings(settings=settings), settings=settings)
