"""Explanation and traceability helpers for semantic inferences."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

REASON = Namespace("https://example.org/semantic-platform/reasoning#")
PROV = Namespace("http://www.w3.org/ns/prov#")

Triple = tuple[URIRef, URIRef, URIRef]


@dataclass(frozen=True)
class Explanation:
    """Human and RDF-serializable explanation for an inferred assertion."""

    assertion: Triple
    rule: URIRef
    source_triples: tuple[Triple, ...]
    engine_version: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    inference: URIRef = field(default_factory=lambda: REASON[f"inference-{uuid4()}"])
    explanation: URIRef = field(default_factory=lambda: REASON[f"explanation-{uuid4()}"])
    confidence: float = 1.0

    def message(self) -> str:
        """Return a concise natural-language explanation."""
        sources = "; ".join(f"{s} {p} {o}" for s, p, o in self.source_triples)
        s, p, o = self.assertion
        return f"{s} {p} {o} was inferred by {self.rule} from {sources}."


def _dt(value: datetime) -> Literal:
    return Literal(value.astimezone(UTC).isoformat().replace("+00:00", "Z"), datatype=XSD.dateTime)


def reified_assertion(graph: Graph, assertion: Triple, node: URIRef) -> None:
    """Represent an RDF triple as a traceable rdf:Statement node."""
    s, p, o = assertion
    graph.add((node, RDF.type, RDF.Statement))
    graph.add((node, RDF.subject, s))
    graph.add((node, RDF.predicate, p))
    graph.add((node, RDF.object, o))


def explanation_graph(explanations: list[Explanation]) -> Graph:
    """Serialize explanations, inferences, source facts, and PROV-O metadata."""
    graph = Graph()
    engine = REASON["engine-lightweight-1"]
    graph.add((engine, RDF.type, REASON.ReasoningEngine))
    graph.add((engine, RDFS.label, Literal("Semantic Platform Lightweight Reasoning Engine")))
    for item in explanations:
        assertion_node = URIRef(f"{item.inference}/assertion")
        reified_assertion(graph, item.assertion, assertion_node)
        graph.add((item.inference, RDF.type, REASON.Inference))
        graph.add((item.inference, REASON.generatedAssertion, assertion_node))
        graph.add((item.inference, REASON.usesRule, item.rule))
        graph.add((item.inference, REASON.executedByEngine, engine))
        graph.add((item.inference, REASON.hasConfidence, Literal(item.confidence, datatype=XSD.decimal)))
        graph.add((item.inference, PROV.generatedAtTime, _dt(item.timestamp)))
        graph.add((item.inference, PROV.wasAssociatedWith, engine))
        graph.add((item.inference, REASON.hasExplanation, item.explanation))
        graph.add((item.explanation, RDF.type, REASON.Explanation))
        graph.add((item.explanation, RDFS.comment, Literal(item.message())))
        graph.add((item.explanation, PROV.generatedAtTime, _dt(item.timestamp)))
        graph.add((item.explanation, REASON.inferredBy, item.inference))
        for index, source in enumerate(item.source_triples, start=1):
            source_node = URIRef(f"{item.inference}/source/{index}")
            reified_assertion(graph, source, source_node)
            graph.add((item.inference, REASON.inferredFrom, source_node))
    return graph
