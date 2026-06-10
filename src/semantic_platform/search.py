"""Full-text, label, and URI search over local semantic platform assets."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

LABEL_PREDICATES = (RDFS.label, SKOS.prefLabel, DCTERMS.title)
TEXT_PREDICATES = LABEL_PREDICATES + (RDFS.comment, DCTERMS.description)


@dataclass(frozen=True)
class SearchResult:
    """Search result for a semantic resource or literal match."""

    uri: str
    label: str
    match_type: str
    predicate: str
    value: str
    resource_type: str


def _label(graph: Graph, resource: URIRef) -> str:
    for predicate in LABEL_PREDICATES:
        value = graph.value(resource, predicate)
        if value is not None:
            return str(value)
    return str(resource)


def _type(graph: Graph, resource: URIRef) -> str:
    value = graph.value(resource, RDF.type)
    return str(value) if value is not None else "Resource"


def _result(
    graph: Graph, resource: URIRef, match_type: str, predicate: str, value: str
) -> SearchResult:
    return SearchResult(
        str(resource), _label(graph, resource), match_type, predicate, value, _type(graph, resource)
    )


def search_graph(
    query: str, graph: Graph | None = None, settings: Settings | None = None, limit: int = 50
) -> list[SearchResult]:
    """Search URI strings, labels, and descriptive text in a graph."""
    graph = graph or load_graph(settings=settings or load_settings())
    needle = query.casefold().strip()
    if not needle:
        return []

    results: list[SearchResult] = []
    seen: set[tuple[str, str, str]] = set()

    for subject in sorted({s for s in graph.subjects() if isinstance(s, URIRef)}, key=str):
        if needle in str(subject).casefold():
            key = (str(subject), "uri", str(subject))
            if key not in seen:
                seen.add(key)
                results.append(_result(graph, subject, "URI", "@id", str(subject)))
        for predicate in TEXT_PREDICATES:
            for value in graph.objects(subject, predicate):
                if isinstance(value, Literal) and needle in str(value).casefold():
                    match_type = "Label" if predicate in LABEL_PREDICATES else "Full text"
                    key = (str(subject), match_type, str(predicate))
                    if key not in seen:
                        seen.add(key)
                        results.append(
                            _result(graph, subject, match_type, str(predicate), str(value))
                        )
        if len(results) >= limit:
            break
    return results[:limit]
