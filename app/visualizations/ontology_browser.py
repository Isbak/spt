"""Ontology browser visualization data service."""

from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from semantic_platform.analytics import ontology_statistics
from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph


def _label(graph: Graph, node: URIRef) -> str:
    return str(graph.value(node, RDFS.label) or node)


def ontology_browser_data(settings: Settings | None = None) -> dict[str, object]:
    """Return classes, hierarchy, properties, and instances for ontology navigation."""
    graph = load_graph(settings=settings or load_settings())
    classes = sorted(
        set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class)),
        key=str,
    )
    class_rows = []
    for cls in classes:
        properties = sorted(set(graph.subjects(RDFS.domain, cls)), key=str)
        instances = sorted(set(graph.subjects(RDF.type, cls)), key=str)
        class_rows.append(
            {
                "uri": str(cls),
                "label": _label(graph, cls),
                "subclasses": [str(s) for s in graph.subjects(RDFS.subClassOf, cls)],
                "properties": [
                    {
                        "uri": str(p),
                        "label": _label(graph, p),
                        "range": str(graph.value(p, RDFS.range) or ""),
                    }
                    for p in properties
                ],
                "instances": [{"uri": str(i), "label": _label(graph, i)} for i in instances],
            }
        )
    properties = [
        {
            "uri": str(p),
            "label": _label(graph, p),
            "domain": str(graph.value(p, RDFS.domain) or ""),
            "range": str(graph.value(p, RDFS.range) or ""),
        }
        for p in sorted(
            set(graph.subjects(RDF.type, OWL.ObjectProperty))
            | set(graph.subjects(RDF.type, OWL.DatatypeProperty))
            | set(graph.subjects(RDF.type, RDF.Property)),
            key=str,
        )
    ]
    ontology = next(iter(graph.subjects(RDF.type, OWL.Ontology)), None)
    return {
        "classes": class_rows,
        "properties": properties,
        "statistics": ontology_statistics(graph),
        "version": str(graph.value(ontology, OWL.versionInfo) or "Not declared")
        if ontology
        else "Not declared",
    }
