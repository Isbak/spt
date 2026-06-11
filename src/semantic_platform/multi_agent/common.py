"""Shared RDF terms for governed multi-agent collaboration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, XSD

MA = Namespace("https://example.org/semantic-platform/multi-agent#")
AGENT = Namespace("https://example.org/semantic-platform/agents#")
AGGOV = Namespace("https://example.org/semantic-platform/agent-governance#")
ORCH = Namespace("https://example.org/semantic-platform/orchestration#")


def now_literal() -> Literal:
    return Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)


def new_uri(prefix: str) -> URIRef:
    return URIRef(MA[f"{prefix}-{uuid4()}"])


def bind(graph: Graph) -> Graph:
    graph.bind("ma", MA)
    graph.bind("agent", AGENT)
    graph.bind("aggov", AGGOV)
    graph.bind("orch", ORCH)
    graph.bind("prov", PROV)
    graph.bind("dcterms", DCTERMS)
    return graph


def local_id(uri: URIRef | str) -> str:
    value = str(uri)
    return value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def text(graph: Graph, subject: URIRef, predicate: URIRef, default: str = "") -> str:
    value = graph.value(subject, predicate)
    return str(value) if value is not None else default


def add_label(graph: Graph, resource: URIRef, label: str) -> None:
    if label:
        graph.add((resource, RDFS.label, Literal(label)))


def add_prov_activity(
    graph: Graph,
    activity_type: URIRef,
    label: str,
    actor: str,
    *,
    used: list[URIRef] | None = None,
    generated: URIRef | None = None,
) -> URIRef:
    bind(graph)
    activity = new_uri("activity")
    actor_uri = URIRef(actor) if actor.startswith("http") else URIRef(MA[actor])
    graph.add((actor_uri, RDF.type, PROV.Agent))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, RDF.type, activity_type))
    graph.add((activity, RDFS.label, Literal(label)))
    graph.add((activity, PROV.startedAtTime, now_literal()))
    graph.add((activity, PROV.endedAtTime, now_literal()))
    graph.add((activity, PROV.wasAssociatedWith, actor_uri))
    for item in used or []:
        graph.add((activity, PROV.used, item))
    if generated is not None:
        graph.add((generated, PROV.wasGeneratedBy, activity))
        graph.add((generated, PROV.wasAttributedTo, actor_uri))
    return activity


def slug(value: str) -> str:
    """Return a URI-safe local identifier fragment."""
    return "-".join(str(value).replace("#", "-").replace("/", "-").split())
