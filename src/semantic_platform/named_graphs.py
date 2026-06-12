"""Named graph manifest services."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS

from semantic_platform.config import DATASET_ROLES, Settings, load_settings
from semantic_platform.graph import load_graph

GOV = Namespace("https://example.org/semantic-platform/governance#")

#: Maps a named graph (by local name) to its storage role (ADR-0017). This is the single
#: source of truth used to route both the relational source a mapping reads from and the
#: Fuseki dataset its output is served to. Graphs not listed default to ``"business"``
#: (domain/instance data is the open-ended category).
GRAPH_DATASET_ROUTING: dict[str, str] = {
    # system: graphs the platform authors or generates itself (never warehouse-sourced).
    "ontology": "system",
    "governance": "system",
    "reasoning": "system",
    "inferred": "system",
    "validation": "system",
    # agents+lineage: agent registry/memory/observations + PROV-O provenance.
    "provenance": "agents",
    "agents": "agents",
    # business: domain/reference/instance data (any graph an R2RML mapping can target).
    "reference": "business",
    "masterdata": "business",
    "transactional": "business",
    "integration": "business",
    "sandbox": "business",
    # Legacy graph name used by api.upload_default_graphs for instance data.
    "data": "business",
}


def _graph_local_name(graph_uri: str) -> str:
    """Return the trailing token of a graph URI (handles ``urn:graph:<x>`` and variants)."""
    text = str(graph_uri)
    for separator in ("#", "/", ":"):
        if separator in text:
            text = text.rsplit(separator, 1)[-1]
    return text


def dataset_for_graph(graph_uri: str) -> str:
    """Return the storage role (``system``/``agents``/``business``) for a named graph.

    Unknown graphs route to ``"business"`` so domain/instance graphs work without being
    enumerated. Used symmetrically for source selection and served-graph upload.
    """
    return GRAPH_DATASET_ROUTING.get(_graph_local_name(graph_uri), "business")


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
    stored_in_dataset: str | None


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
                stored_in_dataset=str(graph.value(graph_ref, GOV.storedInDataset) or "") or None,
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
            "stored-in dataset": record.stored_in_dataset,
        }
        for name, value in required.items():
            if not value:
                errors.append(f"{record.graph} is missing {name}")
        if record.stored_in_dataset and record.stored_in_dataset not in DATASET_ROLES:
            errors.append(
                f"{record.graph} has unknown storedInDataset {record.stored_in_dataset!r}"
            )
    return errors


def graph_lifecycle_summary(settings: Settings | None = None) -> dict[str, object]:
    """Return named graph lifecycle summary data."""
    graph = load_named_graph_manifest(settings=settings)
    records = list_named_graphs(graph=graph)
    return {"named_graph_count": len(records), "named_graphs": records, "errors": validate_named_graph_metadata(graph=graph)}
