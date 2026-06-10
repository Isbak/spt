"""Semantic source catalog registration and query utilities."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings
from semantic_platform.graph import load_graph
from semantic_platform.r2rdf import GOV, MAP


@dataclass(frozen=True)
class SourceDatasetRecord:
    """Source dataset catalog record."""

    iri: str
    label: str
    source_system: str
    owner: str
    steward: str
    version: str


def source_catalog_graph(settings: Settings | None = None) -> Graph:
    """Load the local semantic source catalog."""
    return load_graph(settings=settings)


def register_source_system(graph: Graph, iri: str, label: str) -> URIRef:
    """Register a source system in a graph."""
    resource = URIRef(iri)
    graph.add((resource, RDF.type, MAP.SourceSystem))
    graph.add((resource, RDFS.label, Literal(label)))
    return resource


def register_dataset(
    graph: Graph,
    iri: str,
    label: str,
    source_system: URIRef,
    *,
    version: str,
    owner: URIRef = GOV.platformOwner,
    steward: URIRef = GOV.platformSteward,
) -> URIRef:
    """Register a source dataset, governance ownership, and source version."""
    dataset = URIRef(iri)
    graph.add((dataset, RDF.type, MAP.SourceDataset))
    graph.add((dataset, RDFS.label, Literal(label)))
    graph.add((dataset, MAP.hasSourceSystem, source_system))
    graph.add((dataset, MAP.sourceVersion, Literal(version)))
    graph.add((dataset, GOV.hasOwner, owner))
    graph.add((dataset, GOV.hasSteward, steward))
    return dataset


def register_mapping_ownership(
    graph: Graph,
    mapping: URIRef,
    owner: URIRef = GOV.platformOwner,
    steward: URIRef = GOV.platformSteward,
) -> None:
    """Attach mapping ownership and stewardship metadata."""
    graph.add((mapping, GOV.hasOwner, owner))
    graph.add((mapping, GOV.hasSteward, steward))


def list_source_datasets(settings: Settings | None = None) -> list[SourceDatasetRecord]:
    """Return registered source datasets."""
    graph = source_catalog_graph(settings)
    records: list[SourceDatasetRecord] = []
    for dataset in sorted(set(graph.subjects(RDF.type, MAP.SourceDataset))):
        records.append(
            SourceDatasetRecord(
                iri=str(dataset),
                label=_value(graph, dataset, RDFS.label) or str(dataset),
                source_system=_value(graph, dataset, MAP.hasSourceSystem),
                owner=_value(graph, dataset, GOV.hasOwner),
                steward=_value(graph, dataset, GOV.hasSteward),
                version=_value(graph, dataset, MAP.sourceVersion),
            )
        )
    return records


def _value(graph: Graph, subject: URIRef, predicate: URIRef) -> str:
    value = next(graph.objects(subject, predicate), None)
    return str(value) if value is not None else ""
