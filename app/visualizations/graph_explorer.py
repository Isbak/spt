"""Reusable graph explorer visualization data service."""

from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph


def _label(graph: Graph, node: URIRef) -> str:
    return str(graph.value(node, RDFS.label) or graph.value(node, RDFS.comment) or node)


def _node_type(graph: Graph, node: URIRef) -> str:
    return str(graph.value(node, RDF.type) or "Resource")


def graph_explorer_data(
    node: str | None = None,
    query: str | None = None,
    limit: int = 75,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Return nodes and edges suitable for vis-network rendering."""
    graph = load_graph(settings=settings or load_settings())
    focus = URIRef(node) if node else None
    triples = []
    for triple in sorted(graph, key=lambda item: tuple(map(str, item))):
        subject, predicate, obj = triple
        if not isinstance(subject, URIRef) or not isinstance(obj, URIRef):
            continue
        text = " ".join(map(str, triple)).casefold()
        if focus and focus not in {subject, obj}:
            continue
        if query and query.casefold() not in text:
            continue
        triples.append(triple)
        if len(triples) >= limit:
            break
    node_ids = {term for triple in triples for term in (triple[0], triple[2])}
    nodes = [
        {
            "id": str(term),
            "label": _label(graph, term),
            "type": _node_type(graph, term),
            "group": _node_type(graph, term).rsplit("#", 1)[-1],
            "provenance": str(
                graph.value(term, URIRef("http://www.w3.org/ns/prov#wasGeneratedBy"))
                or "Not recorded"
            ),
        }
        for term in sorted(node_ids, key=str)
    ]
    edges = [
        {"from": str(s), "to": str(o), "label": _label(graph, p), "predicate": str(p)}
        for s, p, o in triples
    ]
    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}
