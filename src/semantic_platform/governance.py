"""Governance metadata services for semantic platform assets."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

GOV = Namespace("https://example.org/semantic-platform/governance#")


@dataclass(frozen=True)
class GovernanceRecord:
    """Governance metadata for one graph asset."""

    asset: str
    label: str
    owner: str | None
    steward: str | None
    classification: str | None


def _label(graph: Graph, node: URIRef | None) -> str | None:
    if node is None:
        return None
    value = graph.value(node, RDFS.label)
    return str(value) if value is not None else str(node)


def load_governance_metadata(settings: Settings | None = None, graph: Graph | None = None) -> Graph:
    """Load governance metadata from local RDF assets."""
    settings = settings or load_settings()
    return graph or load_graph([settings.vocabularies_dir, settings.graphs_dir, settings.data_dir], settings)


def graph_assets(graph: Graph | None = None, settings: Settings | None = None) -> list[GovernanceRecord]:
    """Return governance records for all declared graph assets."""
    graph = load_governance_metadata(settings=settings, graph=graph)
    records: list[GovernanceRecord] = []
    for asset in sorted(graph.subjects(RDF.type, GOV.GraphAsset), key=str):
        owner = graph.value(asset, GOV.hasOwner)
        steward = graph.value(asset, GOV.hasSteward)
        classification = graph.value(asset, GOV.hasClassification)
        records.append(
            GovernanceRecord(
                asset=str(asset),
                label=_label(graph, asset) or str(asset),
                owner=_label(graph, owner) if isinstance(owner, URIRef) else None,
                steward=_label(graph, steward) if isinstance(steward, URIRef) else None,
                classification=_label(graph, classification) if isinstance(classification, URIRef) else None,
            )
        )
    return records


def query_owners_and_stewards(graph: Graph | None = None, settings: Settings | None = None) -> dict[str, dict[str, str | None]]:
    """Return owner and steward labels by graph asset IRI."""
    return {record.asset: {"owner": record.owner, "steward": record.steward} for record in graph_assets(graph, settings)}


def validate_graph_governance(graph: Graph | None = None, settings: Settings | None = None) -> list[str]:
    """Validate graph assets have owner, steward, and classification metadata."""
    graph = load_governance_metadata(settings=settings, graph=graph)
    errors: list[str] = []
    for asset in sorted(graph.subjects(RDF.type, GOV.GraphAsset), key=str):
        for predicate, name in [
            (GOV.hasOwner, "owner"),
            (GOV.hasSteward, "steward"),
            (GOV.hasClassification, "classification"),
        ]:
            if graph.value(asset, predicate) is None:
                errors.append(f"{asset} is missing {name}")
    return errors


def governance_summary(settings: Settings | None = None) -> dict[str, object]:
    """Return a simple governance summary for UI, Make targets, and tests."""
    graph = load_governance_metadata(settings=settings)
    records = graph_assets(graph=graph)
    errors = validate_graph_governance(graph=graph)
    return {"graph_asset_count": len(records), "graph_assets": records, "errors": errors}


def enterprise_governance_summary(graph: Graph | None = None, settings: Settings | None = None) -> dict[str, int]:
    """Return governance counts for Phase 10 enterprise asset classes."""
    settings = settings or load_settings()
    graph = graph or load_governance_metadata(settings=settings)
    fabric = Namespace("https://example.org/semantic-platform/knowledge-fabric#")
    return {
        "domain_governance": len(set(graph.subjects(RDF.type, fabric.DomainGovernance))),
        "product_governance": len(set(graph.subjects(RDF.type, fabric.ProductGovernance))),
        "contract_governance": len(set(graph.subjects(RDF.type, fabric.ContractGovernance))),
        "ontology_governance": len(set(graph.subjects(RDF.type, fabric.OntologyGovernance))),
        "agent_governance": len(set(graph.subjects(RDF.type, fabric.AgentGovernance))),
    }
