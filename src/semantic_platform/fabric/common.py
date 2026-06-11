"""Common helpers for the Enterprise Knowledge Fabric."""

from __future__ import annotations

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS

FABRIC = Namespace("https://example.org/semantic-platform/knowledge-fabric#")
CONTRACT = Namespace("https://example.org/semantic-platform/contracts#")
GOV = Namespace("https://example.org/semantic-platform/governance#")
PROV = Namespace("http://www.w3.org/ns/prov#")
EX = Namespace("https://example.org/semantic-platform/data#")


def bind(graph: Graph) -> Graph:
    graph.bind("fabric", FABRIC)
    graph.bind("contract", CONTRACT)
    graph.bind("gov", GOV)
    graph.bind("prov", PROV)
    graph.bind("ex", EX)
    return graph


def text(graph: Graph, subject: URIRef, predicate: URIRef, default: str = "") -> str:
    value = graph.value(subject, predicate)
    return str(value) if value is not None else default


def labels(graph: Graph, subject: URIRef, predicate: URIRef) -> tuple[str, ...]:
    return tuple(label(graph, value) for value in graph.objects(subject, predicate) if isinstance(value, URIRef))


def label(graph: Graph, node: URIRef) -> str:
    value = graph.value(node, RDFS.label)
    return str(value) if value is not None else str(node).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def local_id(node: URIRef | str) -> str:
    value = str(node)
    return value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
