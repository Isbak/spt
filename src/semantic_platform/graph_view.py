"""Graph-view builders: turn an RDF graph into node/edge and node-detail payloads.

These are pure, ``rdflib``-only helpers shared by the System Graph Explorer and the
Studio's workspace graph view. They live in the package (not the Flask layer) so
:mod:`semantic_platform.api` can expose workspace variants without the package
importing from ``app`` (see CLAUDE.md: the package must never import from ``app``).
"""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

_PROV_GENERATED_BY = URIRef("http://www.w3.org/ns/prov#wasGeneratedBy")


def _label(graph: Graph, node: URIRef) -> str:
    """Human label for a term: rdfs:label → rdfs:comment → the URI itself."""
    return str(graph.value(node, RDFS.label) or graph.value(node, RDFS.comment) or node)


def _node_type(graph: Graph, node: URIRef) -> str:
    """Primary rdf:type of a term, or ``"Resource"`` when untyped."""
    return str(graph.value(node, RDF.type) or "Resource")


def _local_name(uri: str) -> str:
    """The fragment/last path segment of a URI — used for type grouping/legends."""
    return uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or uri


def build_graph_view(
    graph: Graph,
    node: str | None = None,
    query: str | None = None,
    limit: int = 75,
) -> dict[str, object]:
    """Return ``{nodes, edges, node_count, edge_count}`` for vis-network rendering.

    ``node`` focuses on triples touching that URI; ``query`` is a case-insensitive
    substring filter over each triple's text. Only URIRef↔URIRef triples are kept
    (literals are surfaced in :func:`node_detail`, not as graph nodes).
    """
    focus = URIRef(node) if node else None
    triples = []
    for triple in sorted(graph, key=lambda item: tuple(map(str, item))):
        subject, _predicate, obj = triple
        if not isinstance(subject, URIRef) or not isinstance(obj, URIRef):
            continue
        if focus and focus not in {subject, obj}:
            continue
        if query and query.casefold() not in " ".join(map(str, triple)).casefold():
            continue
        triples.append(triple)
        if len(triples) >= limit:
            break

    node_ids = {term for triple in triples for term in (triple[0], triple[2])}
    degree: dict[URIRef, int] = {term: 0 for term in node_ids}
    for subject, _predicate, obj in triples:
        degree[subject] += 1
        degree[obj] += 1

    nodes = []
    for term in sorted(node_ids, key=str):
        type_uri = _node_type(graph, term)
        label = _label(graph, term)
        nodes.append(
            {
                "id": str(term),
                "label": label,
                "type": type_uri,
                "group": _local_name(type_uri),
                "provenance": str(graph.value(term, _PROV_GENERATED_BY) or "Not recorded"),
                "degree": degree.get(term, 0),
                "title": f"{label}\n{_local_name(type_uri)} · {degree.get(term, 0)} links",
            }
        )

    edges = []
    for index, (subject, predicate, obj) in enumerate(triples):
        predicate_label = _label(graph, predicate)
        edges.append(
            {
                "id": f"e{index}",
                "from": str(subject),
                "to": str(obj),
                "label": predicate_label,
                "predicate": str(predicate),
                "title": predicate_label,
            }
        )

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


def node_detail(graph: Graph, uri: str) -> dict[str, object]:
    """Return the full inspectable detail for a single resource (the sidebar payload).

    Literals become ``properties``; URIRef objects become ``outgoing`` relationships;
    statements where the resource is the object become ``incoming`` relationships.
    ``rdf:type`` is reported via ``types``/``type_labels`` rather than as an edge.
    """
    resource = URIRef(uri)

    types: list[str] = []
    type_labels: list[str] = []
    properties: list[dict[str, str]] = []
    outgoing: list[dict[str, str]] = []
    for predicate, obj in graph.predicate_objects(resource):
        if predicate == RDF.type:
            types.append(str(obj))
            type_labels.append(_label(graph, obj) if isinstance(obj, URIRef) else str(obj))
        elif isinstance(obj, Literal):
            properties.append(
                {
                    "predicate": str(predicate),
                    "predicate_label": _label(graph, predicate),
                    "value": str(obj),
                }
            )
        elif isinstance(obj, URIRef):
            outgoing.append(
                {
                    "predicate": str(predicate),
                    "predicate_label": _label(graph, predicate),
                    "target": str(obj),
                    "target_label": _label(graph, obj),
                }
            )

    incoming: list[dict[str, str]] = []
    for subject, predicate in graph.subject_predicates(resource):
        if isinstance(subject, URIRef):
            incoming.append(
                {
                    "predicate": str(predicate),
                    "predicate_label": _label(graph, predicate),
                    "source": str(subject),
                    "source_label": _label(graph, subject),
                }
            )

    return {
        "id": str(resource),
        "label": _label(graph, resource),
        "types": types,
        "type_labels": type_labels,
        "comment": str(graph.value(resource, RDFS.comment) or ""),
        "provenance": str(graph.value(resource, _PROV_GENERATED_BY) or "Not recorded"),
        "properties": sorted(properties, key=lambda item: item["predicate_label"]),
        "outgoing": sorted(outgoing, key=lambda item: item["predicate_label"]),
        "incoming": sorted(incoming, key=lambda item: item["predicate_label"]),
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
    }
