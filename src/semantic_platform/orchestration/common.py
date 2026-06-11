"""Shared RDF terms for semantic orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, XSD

ORCH = Namespace("https://example.org/semantic-platform/orchestration#")
AGENT = Namespace("https://example.org/semantic-platform/agents#")
AGGOV = Namespace("https://example.org/semantic-platform/agent-governance#")


def new_uri(prefix: str) -> URIRef:
    """Return a stable namespace URI with a generated local identifier."""
    return URIRef(ORCH[f"{prefix}-{uuid4()}"])


def bind(graph: Graph) -> Graph:
    """Bind common prefixes and return ``graph`` for fluent construction."""
    graph.bind("orch", ORCH)
    graph.bind("agent", AGENT)
    graph.bind("aggov", AGGOV)
    graph.bind("prov", PROV)
    graph.bind("dcterms", DCTERMS)
    return graph


def text(graph: Graph, subject: URIRef, predicate: URIRef, default: str = "") -> str:
    """Read one RDF literal or URI as text."""
    value = graph.value(subject, predicate)
    return str(value) if value is not None else default


def local_id(uri: URIRef | str) -> str:
    """Return the local id of a URI-like string."""
    value = str(uri)
    return value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def add_label(graph: Graph, resource: URIRef, label: str) -> None:
    """Add a human-readable label when supplied."""
    if label:
        graph.add((resource, RDFS.label, Literal(label)))


def add_activity(
    graph: Graph,
    activity_type: URIRef,
    label: str,
    *,
    planner: str = "semantic-orchestration-layer",
    used: list[URIRef] | None = None,
    generated: URIRef | None = None,
) -> URIRef:
    """Create a PROV-O activity record for orchestration actions."""
    bind(graph)
    activity = new_uri("activity")
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, RDF.type, activity_type))
    graph.add((activity, RDFS.label, Literal(label)))
    graph.add((activity, PROV.startedAtTime, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
    graph.add((activity, PROV.endedAtTime, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
    agent = URIRef(ORCH[planner])
    graph.add((agent, RDF.type, PROV.Agent))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    for item in used or []:
        graph.add((activity, PROV.used, item))
    if generated is not None:
        graph.add((generated, PROV.wasGeneratedBy, activity))
    return activity
