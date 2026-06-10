"""Ontology version metadata services."""

from __future__ import annotations

from dataclasses import dataclass
import re

from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, RDF

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True)
class OntologyMetadata:
    """Version metadata for one ontology."""

    ontology: str
    version: str
    created: str | None
    modified: str | None
    creator: str | None
    publisher: str | None


def validate_version_format(version: str) -> bool:
    """Return whether a version uses MAJOR.MINOR.PATCH semantic version format."""
    return bool(SEMVER_RE.match(version))


def compare_ontology_versions(left: str, right: str) -> int:
    """Compare two semantic ontology versions."""
    if not validate_version_format(left) or not validate_version_format(right):
        raise ValueError("Ontology versions must use MAJOR.MINOR.PATCH format")
    left_parts = tuple(int(part) for part in left.split("."))
    right_parts = tuple(int(part) for part in right.split("."))
    return (left_parts > right_parts) - (left_parts < right_parts)


def load_ontology_graph(settings: Settings | None = None, graph: Graph | None = None) -> Graph:
    """Load ontology and vocabulary RDF that can contain ontology declarations."""
    settings = settings or load_settings()
    return graph or load_graph([settings.ontology_dir, settings.vocabularies_dir], settings)


def ontology_metadata(settings: Settings | None = None, graph: Graph | None = None) -> list[OntologyMetadata]:
    """Report metadata for all ontology declarations."""
    graph = load_ontology_graph(settings=settings, graph=graph)
    records: list[OntologyMetadata] = []
    for ontology in sorted(graph.subjects(RDF.type, OWL.Ontology), key=str):
        version = str(graph.value(ontology, OWL.versionInfo) or "")
        records.append(
            OntologyMetadata(
                ontology=str(ontology),
                version=version,
                created=str(graph.value(ontology, DCTERMS.created) or "") or None,
                modified=str(graph.value(ontology, DCTERMS.modified) or "") or None,
                creator=str(graph.value(ontology, DCTERMS.creator) or "") or None,
                publisher=str(graph.value(ontology, DCTERMS.publisher) or "") or None,
            )
        )
    return records


def extract_ontology_version(ontology_iri: str | None = None, settings: Settings | None = None) -> str | None:
    """Extract an ontology version, optionally for a specific ontology IRI."""
    records = ontology_metadata(settings=settings)
    for record in records:
        if ontology_iri is None or record.ontology == ontology_iri:
            return record.version
    return None


def ontology_version_summary(settings: Settings | None = None) -> dict[str, object]:
    """Return ontology metadata and invalid version entries."""
    records = ontology_metadata(settings=settings)
    invalid = [record for record in records if not validate_version_format(record.version)]
    return {"ontology_count": len(records), "ontologies": records, "invalid_versions": invalid}
