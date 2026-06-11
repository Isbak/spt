"""Shared RDF terms for governed semantic execution."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, XSD

EXEC = Namespace("https://example.org/semantic-platform/execution#")
ORCH = Namespace("https://example.org/semantic-platform/orchestration#")


def new_uri(prefix: str) -> URIRef:
    return URIRef(EXEC[f"{prefix}-{uuid4()}"])


def bind(graph: Graph) -> Graph:
    graph.bind("exec", EXEC)
    graph.bind("orch", ORCH)
    graph.bind("prov", PROV)
    graph.bind("dcterms", DCTERMS)
    return graph


def add_label(graph: Graph, subject: URIRef, label: str) -> None:
    if label:
        graph.add((subject, RDFS.label, Literal(label)))


def text(graph: Graph, subject: URIRef, predicate: URIRef, default: str = "") -> str:
    value = graph.value(subject, predicate)
    return str(value) if value is not None else default


def add_activity(
    graph: Graph,
    activity_type: URIRef,
    label: str,
    *,
    actor: str = "semantic-execution-layer",
    used: list[URIRef] | None = None,
    generated: URIRef | None = None,
) -> URIRef:
    bind(graph)
    activity = new_uri("activity")
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, RDF.type, activity_type))
    graph.add((activity, RDFS.label, Literal(label)))
    now = Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)
    graph.add((activity, PROV.startedAtTime, now))
    graph.add((activity, PROV.endedAtTime, now))
    agent = URIRef(EXEC[actor])
    graph.add((agent, RDF.type, PROV.Agent))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    for item in used or []:
        graph.add((activity, PROV.used, item))
    if generated is not None:
        graph.add((generated, PROV.wasGeneratedBy, activity))
    return activity
