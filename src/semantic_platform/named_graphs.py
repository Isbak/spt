"""Named graph manifest services."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

GOV = Namespace("https://example.org/semantic-platform/governance#")


@dataclass(frozen=True)
class NamedGraphRecord:
    """Named graph lifecycle metadata from the manifest."""

    graph: str
    label: str
    description: str | None
    owner: str | None
    steward: str | None
    classification: str | None
    lifecycle_status: str | None
    intended_use: str | None
    allowed_write_pattern: str | None


def _label(graph: Graph, node: URIRef | None) -> str | None:
    if node is None:
        return None
    value = graph.value(node, RDFS.label)
    return str(value) if value is not None else str(node)


def load_named_graph_manifest(settings: Settings | None = None, graph: Graph | None = None) -> Graph:
    """Load the named graph manifest and governance vocabulary."""
    settings = settings or load_settings()
    return graph or load_graph([settings.vocabularies_dir, settings.graphs_dir / "manifest.ttl"], settings)


def list_named_graphs(graph: Graph | None = None, settings: Settings | None = None) -> list[NamedGraphRecord]:
    """List known named graphs with lifecycle metadata."""
    graph = load_named_graph_manifest(settings=settings, graph=graph)
    records: list[NamedGraphRecord] = []
    for graph_ref in sorted(graph.subjects(RDF.type, GOV.GraphAsset), key=str):
        records.append(
            NamedGraphRecord(
                graph=str(graph_ref),
                label=_label(graph, graph_ref) or str(graph_ref),
                description=str(graph.value(graph_ref, DCTERMS.description) or "") or None,
                owner=_label(graph, graph.value(graph_ref, GOV.hasOwner)),
                steward=_label(graph, graph.value(graph_ref, GOV.hasSteward)),
                classification=_label(graph, graph.value(graph_ref, GOV.hasClassification)),
                lifecycle_status=_label(graph, graph.value(graph_ref, GOV.hasLifecycleStatus)),
                intended_use=str(graph.value(graph_ref, GOV.intendedUse) or "") or None,
                allowed_write_pattern=_label(graph, graph.value(graph_ref, GOV.hasAllowedWritePattern)),
            )
        )
    return records


def validate_named_graph_metadata(graph: Graph | None = None, settings: Settings | None = None) -> list[str]:
    """Validate that every manifest graph has lifecycle metadata."""
    errors: list[str] = []
    for record in list_named_graphs(graph=graph, settings=settings):
        required = {
            "label": record.label,
            "description": record.description,
            "owner": record.owner,
            "steward": record.steward,
            "classification": record.classification,
            "lifecycle status": record.lifecycle_status,
            "intended use": record.intended_use,
            "allowed write pattern": record.allowed_write_pattern,
        }
        for name, value in required.items():
            if not value:
                errors.append(f"{record.graph} is missing {name}")
    return errors


def graph_lifecycle_summary(settings: Settings | None = None) -> dict[str, object]:
    """Return named graph lifecycle summary data."""
    graph = load_named_graph_manifest(settings=settings)
    records = list_named_graphs(graph=graph)
    return {"named_graph_count": len(records), "named_graphs": records, "errors": validate_named_graph_metadata(graph=graph)}
