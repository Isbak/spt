"""Semantic consistency validation for RDF knowledge graphs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph
from semantic_platform.rule_registry import REASON, load_rule_registry

SH = Namespace("http://www.w3.org/ns/shacl#")


@dataclass(frozen=True)
class ConsistencyIssue:
    """One semantic consistency finding."""

    focus_node: str
    severity: str
    message: str
    check: str


@dataclass(frozen=True)
class ConsistencyReport:
    """Consistency validation output."""

    conforms: bool
    issues: list[ConsistencyIssue]
    graph: Graph


def _declared_resources(graph: Graph) -> set[URIRef]:
    resources: set[URIRef] = set()
    for subject in graph.subjects():
        if isinstance(subject, URIRef):
            resources.add(subject)
    for obj in graph.objects(None, RDF.type):
        if isinstance(obj, URIRef):
            resources.add(obj)
    return resources


def _references(graph: Graph) -> set[URIRef]:
    refs: set[URIRef] = set()
    for obj in graph.objects():
        if isinstance(obj, URIRef):
            refs.add(obj)
    return refs


def _cycle_issues(graph: Graph, predicate: URIRef) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    adjacency: dict[URIRef, set[URIRef]] = {}
    for source, target in graph.subject_objects(predicate):
        if isinstance(source, URIRef) and isinstance(target, URIRef):
            if predicate == RDFS.subClassOf and (
                (source, OWL.equivalentClass, target) in graph
                or (target, OWL.equivalentClass, source) in graph
            ):
                continue
            if predicate == RDFS.subPropertyOf and (
                (source, OWL.equivalentProperty, target) in graph
                or (target, OWL.equivalentProperty, source) in graph
            ):
                continue
            adjacency.setdefault(source, set()).add(target)

    def visit(start: URIRef, node: URIRef, seen: set[URIRef]) -> bool:
        for nxt in adjacency.get(node, set()):
            if nxt == start:
                return True
            if nxt not in seen and visit(start, nxt, seen | {nxt}):
                return True
        return False

    for node in sorted(adjacency, key=str):
        if visit(node, node, {node}):
            issues.append(ConsistencyIssue(str(node), "Violation", f"Cycle detected through {predicate}", "cyclic-structures"))
    return issues


def validate_consistency(graph: Graph | None = None, settings: Settings | None = None) -> ConsistencyReport:
    """Validate missing types, broken references, disallowed cycles, and rule governance."""
    settings = settings or load_settings()
    graph = graph or load_graph(settings=settings)
    issues: list[ConsistencyIssue] = []
    for subject in sorted({s for s in graph.subjects() if isinstance(s, URIRef)}, key=str):
        if not any(graph.objects(subject, RDF.type)) and not str(subject).startswith((str(RDF), str(RDFS), str(OWL), str(REASON))):
            issues.append(ConsistencyIssue(str(subject), "Warning", "Resource has no rdf:type", "missing-types"))
    declared = _declared_resources(graph)
    for ref in sorted(_references(graph) - declared, key=str):
        if str(ref).startswith((str(RDF), str(RDFS), str(OWL), str(XSD), "http://purl.org/dc/terms/", "http://www.w3.org/ns/prov#", "http://www.w3.org/ns/shacl#")):
            continue
        issues.append(ConsistencyIssue(str(ref), "Warning", "Referenced resource is not declared as a subject or class", "broken-references"))
    issues.extend(_cycle_issues(graph, RDFS.subClassOf))
    issues.extend(_cycle_issues(graph, RDFS.subPropertyOf))
    for rule in load_rule_registry(settings=settings, graph=graph).all():
        if not rule.owner or rule.owner == "Unassigned":
            issues.append(ConsistencyIssue(str(rule.iri), "Violation", "Rule is missing owner", "rule-violations"))
        if not rule.steward or rule.steward == "Unassigned":
            issues.append(ConsistencyIssue(str(rule.iri), "Violation", "Rule is missing steward", "rule-violations"))
        if not rule.version or rule.version == "0.0.0":
            issues.append(ConsistencyIssue(str(rule.iri), "Violation", "Rule is missing version", "rule-violations"))
    report_graph = consistency_report_graph(issues)
    return ConsistencyReport(not any(issue.severity == "Violation" for issue in issues), issues, report_graph)


def consistency_report_graph(issues: list[ConsistencyIssue]) -> Graph:
    """Serialize consistency findings as RDF validation results."""
    graph = Graph()
    report = REASON[f"consistency-report-{uuid4()}"]
    graph.add((report, RDF.type, REASON.ConsistencyCheck))
    graph.add((report, REASON.executedByEngine, REASON["engine-lightweight-1"]))
    graph.add((report, RDFS.label, Literal("Semantic consistency report")))
    graph.add((report, REASON.generatedAt, Literal(datetime.now(UTC).isoformat().replace("+00:00", "Z"), datatype=XSD.dateTime)))
    for issue in issues:
        result = BNode()
        graph.add((report, SH.result, result))
        graph.add((result, RDF.type, SH.ValidationResult))
        graph.add((result, SH.focusNode, URIRef(issue.focus_node)))
        graph.add((result, SH.resultMessage, Literal(issue.message)))
        graph.add((result, SH.sourceConstraintComponent, Literal(issue.check)))
        graph.add((result, SH.resultSeverity, SH.Violation if issue.severity == "Violation" else SH.Warning))
    return graph
