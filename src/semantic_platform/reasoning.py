"""Semantic reasoning orchestration and graph management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from semantic_platform.config import Settings, load_settings
from semantic_platform.consistency import ConsistencyReport, validate_consistency
from semantic_platform.explanation import explanation_graph
from semantic_platform.graph import load_graph
from semantic_platform.inference import InferenceResult, infer_owl_patterns, infer_rdfs, infer_rules
from semantic_platform.rule_registry import REASON, RuleRegistry, load_rule_registry

PROV = Namespace("http://www.w3.org/ns/prov#")

REASONING_GRAPH = URIRef("urn:graph:reasoning")
INFERRED_GRAPH = URIRef("urn:graph:inferred")
VALIDATION_GRAPH = URIRef("urn:graph:validation")
ENGINE_VERSION = "semantic-platform-lightweight-reasoner/0.4.0"


@dataclass(frozen=True)
class ReasoningRun:
    """Reasoning execution summary."""

    source_graph: Graph
    inferred_graph: Graph
    reasoning_graph: Graph
    validation_graph: Graph
    consistency: ConsistencyReport
    rules_used: list[str]
    started_at: datetime
    ended_at: datetime
    engine_version: str = ENGINE_VERSION

    @property
    def inferred_count(self) -> int:
        """Return inferred assertion count."""
        return len(self.inferred_graph)

    @property
    def explanation_count(self) -> int:
        """Return explanation count."""
        return len(list(self.reasoning_graph.subjects(RDF.type, REASON.Explanation)))


def _dt(value: datetime) -> Literal:
    return Literal(value.astimezone(UTC).isoformat().replace("+00:00", "Z"), datatype=XSD.dateTime)


def provenance_for_run(started_at: datetime, ended_at: datetime, rules_used: list[URIRef]) -> Graph:
    """Create PROV-O metadata for a reasoning execution."""
    graph = Graph()
    activity = REASON[f"execution-{started_at.strftime('%Y%m%d%H%M%S%f')}"]
    engine = REASON["engine-lightweight-1"]
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, RDF.type, REASON.ReasoningEngineExecution))
    graph.add((activity, RDFS.label, Literal("Semantic reasoning execution")))
    graph.add((activity, PROV.startedAtTime, _dt(started_at)))
    graph.add((activity, PROV.endedAtTime, _dt(ended_at)))
    graph.add((activity, PROV.wasAssociatedWith, engine))
    graph.add((engine, RDF.type, PROV.Agent))
    graph.add((engine, RDF.type, REASON.ReasoningEngine))
    graph.add((engine, REASON.engineVersion, Literal(ENGINE_VERSION)))
    inferred_entity = URIRef("urn:graph:inferred")
    graph.add((inferred_entity, RDF.type, PROV.Entity))
    graph.add((inferred_entity, PROV.wasGeneratedBy, activity))
    for rule in rules_used:
        graph.add((activity, REASON.usesRule, rule))
    return graph


def run_reasoning(graph: Graph | None = None, settings: Settings | None = None, registry: RuleRegistry | None = None) -> ReasoningRun:
    """Run RDFS, OWL-compatible, governed rules, explanations, provenance, and validation."""
    settings = settings or load_settings()
    source_graph = graph or load_graph(settings=settings)
    registry = registry or load_rule_registry(settings=settings, graph=source_graph)
    executable_rules = registry.executable()
    started = datetime.now(UTC)
    result = InferenceResult()
    infer_rdfs(source_graph, result, ENGINE_VERSION)
    infer_owl_patterns(source_graph, result, ENGINE_VERSION)
    infer_rules(source_graph, result, executable_rules, ENGINE_VERSION)
    ended = datetime.now(UTC)
    reasoning_graph = explanation_graph(result.explanations)
    rules_used = sorted({explanation.rule for explanation in result.explanations}, key=str)
    reasoning_graph += provenance_for_run(started, ended, rules_used)
    validation = validate_consistency(source_graph + result.inferred_graph + reasoning_graph, settings=settings)
    return ReasoningRun(
        source_graph=source_graph,
        inferred_graph=result.inferred_graph,
        reasoning_graph=reasoning_graph,
        validation_graph=validation.graph,
        consistency=validation,
        rules_used=[str(rule) for rule in rules_used],
        started_at=started,
        ended_at=ended,
    )


def reasoning_summary(settings: Settings | None = None) -> dict[str, object]:
    """Return UI and CLI-friendly reasoning statistics."""
    run = run_reasoning(settings=settings)
    registry = load_rule_registry(settings=settings, graph=run.source_graph)
    return {
        "engine_version": run.engine_version,
        "rules": registry.all(),
        "rules_used": run.rules_used,
        "inferred_count": run.inferred_count,
        "explanation_count": run.explanation_count,
        "consistency_conforms": run.consistency.conforms,
        "consistency_issues": run.consistency.issues,
        "graphs": [str(REASONING_GRAPH), str(INFERRED_GRAPH), str(VALIDATION_GRAPH)],
    }
