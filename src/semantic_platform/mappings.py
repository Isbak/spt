"""Mapping metadata discovery and catalog services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.r2rdf import GOV, MAP, RR, mapping_files, validate_mapping_file


@dataclass(frozen=True)
class MappingRecord:
    """Catalog record for a semantic mapping."""

    iri: str
    label: str
    version: str
    owner: str
    steward: str
    source: str
    target_graph: str
    status: str


def discover_mapping_files(settings: Settings | None = None) -> list[Path]:
    """Discover R2RML mapping files in the repository."""
    return mapping_files(settings)


def mapping_catalog_graph(settings: Settings | None = None) -> Graph:
    """Load mapping metadata, source catalog, vocabularies, and mapping definitions."""
    settings = settings or load_settings()
    graph = load_graph(settings=settings)
    for path in discover_mapping_files(settings):
        graph.parse(path, format="turtle")
    return graph


def list_mappings(settings: Settings | None = None) -> list[MappingRecord]:
    """List mappings with owner, steward, source, version, status, and target graph."""
    graph = mapping_catalog_graph(settings)
    records: list[MappingRecord] = []
    for mapping in sorted(set(graph.subjects(RDF.type, MAP.Mapping)) | set(graph.subjects(RDF.type, RR.TriplesMap))):
        records.append(
            MappingRecord(
                iri=str(mapping),
                label=_value(graph, mapping, RDFS.label) or str(mapping),
                version=_value(graph, mapping, MAP.version),
                owner=_value(graph, mapping, GOV.hasOwner),
                steward=_value(graph, mapping, GOV.hasSteward),
                source=_value(graph, mapping, MAP.sourcedFrom),
                target_graph=_value(graph, mapping, MAP.targetGraph),
                status=_value(graph, mapping, MAP.mappingStatus) or "defined",
            )
        )
    return records


def validate_catalog(settings: Settings | None = None) -> dict[str, list[str]]:
    """Validate all discovered mapping files and return errors by file."""
    failures: dict[str, list[str]] = {}
    for path in discover_mapping_files(settings):
        result = validate_mapping_file(path)
        if not result.valid:
            failures[str(path)] = result.errors
    return failures


def _value(graph: Graph, subject: URIRef, predicate: URIRef) -> str:
    value = next(graph.objects(subject, predicate), None)
    return str(value) if value is not None else ""
