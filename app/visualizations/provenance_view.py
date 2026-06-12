"""Provenance explorer visualization data service."""

from __future__ import annotations

from rdflib import URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.analytics import provenance_metrics
from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.provenance import PROV


def _label(graph, node):
    return str(graph.value(node, RDFS.label) or node)


def provenance_view_data(settings: Settings | None = None) -> dict[str, object]:
    """Return PROV-O lineage nodes and edges for the given context."""
    settings = settings or load_settings()
    graph = load_graph([settings.vocabularies_dir, settings.data_dir], settings=settings)
    activities = [
        {
            "uri": str(a),
            "label": _label(graph, a),
            "agent": str(graph.value(a, PROV.wasAssociatedWith) or ""),
        }
        for a in sorted(graph.subjects(RDF.type, PROV.Activity), key=str)
    ]
    entities = [
        {
            "uri": str(e),
            "label": _label(graph, e),
            "generated_by": str(graph.value(e, PROV.wasGeneratedBy) or ""),
        }
        for e in sorted(
            set(graph.subjects(RDF.type, PROV.Entity))
            | set(graph.subjects(PROV.wasDerivedFrom, None)),
            key=str,
        )
        if isinstance(e, URIRef)
    ]
    edges = [
        {"from": str(s), "to": str(o), "label": "was derived from"}
        for s, o in sorted(
            graph.subject_objects(PROV.wasDerivedFrom), key=lambda item: tuple(map(str, item))
        )
    ]
    return {
        "activities": activities,
        "entities": entities,
        "edges": edges,
        "metrics": provenance_metrics(graph),
    }
