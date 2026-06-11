"""Semantic analytics services for Phase 5 dashboards."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from semantic_platform.config import Settings, load_settings
from semantic_platform.governance import graph_assets, load_governance_metadata
from semantic_platform.graph import load_graph
from semantic_platform.reasoning import run_reasoning

PROV = Namespace("http://www.w3.org/ns/prov#")
REASON = Namespace("https://example.org/semantic-platform/reasoning#")


@dataclass(frozen=True)
class AnalyticsSummary:
    """Cross-domain analytics used by visualization dashboards."""

    node_count: int
    edge_count: int
    graph_density: float
    class_count: int
    property_count: int
    hierarchy_depth: int
    ownership_coverage: float
    steward_coverage: float
    lineage_depth: int
    activity_count: int
    inferred_triples: int
    inference_ratio: float

    def as_dict(self) -> dict[str, int | float]:
        """Return a JSON/template-friendly representation."""
        return self.__dict__.copy()


def _subjects_objects(graph: Graph) -> set[URIRef]:
    return {
        node for node in set(graph.subjects()) | set(graph.objects()) if isinstance(node, URIRef)
    }


def graph_density(graph: Graph) -> float:
    """Calculate directed graph density from RDF resources and triples."""
    nodes = len(_subjects_objects(graph))
    if nodes < 2:
        return 0.0
    return round(len(graph) / (nodes * (nodes - 1)), 6)


def ontology_statistics(graph: Graph) -> dict[str, int]:
    """Return class, property, and hierarchy-depth metrics."""
    classes = set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class))
    properties = (
        set(graph.subjects(RDF.type, RDF.Property))
        | set(graph.subjects(RDF.type, OWL.ObjectProperty))
        | set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    )
    return {
        "class_count": len(classes),
        "property_count": len(properties),
        "hierarchy_depth": hierarchy_depth(graph, classes),
    }


def hierarchy_depth(graph: Graph, classes: set[URIRef] | None = None) -> int:
    """Return maximum rdfs:subClassOf path depth for ontology classes."""
    classes = classes or (
        set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class))
    )

    def depth(node: URIRef, seen: frozenset[URIRef]) -> int:
        parents = [
            p
            for p in graph.objects(node, RDFS.subClassOf)
            if isinstance(p, URIRef) and p not in seen
        ]
        if not parents:
            return 1 if node in classes else 0
        return 1 + max(depth(parent, seen | {node}) for parent in parents)

    return max((depth(cls, frozenset()) for cls in classes), default=0)


def governance_metrics(
    graph: Graph | None = None, settings: Settings | None = None
) -> dict[str, int | float]:
    """Calculate governance coverage metrics across governed assets."""
    graph = load_governance_metadata(settings=settings, graph=graph)
    assets = graph_assets(graph=graph)
    total = len(assets)
    owned = sum(1 for asset in assets if asset.owner)
    stewarded = sum(1 for asset in assets if asset.steward)
    deprecated = sum(1 for asset in assets if "deprecated" in (asset.classification or "").lower())
    return {
        "asset_count": total,
        "assets_without_owner": total - owned,
        "assets_without_steward": total - stewarded,
        "deprecated_assets": deprecated,
        "ownership_coverage": round(owned / total, 4) if total else 1.0,
        "steward_coverage": round(stewarded / total, 4) if total else 1.0,
        "governance_completeness": round((owned + stewarded) / (total * 2), 4) if total else 1.0,
    }


def provenance_metrics(graph: Graph) -> dict[str, int]:
    """Calculate provenance lineage and activity metrics."""
    activities = set(graph.subjects(RDF.type, PROV.Activity))
    entities = set(graph.subjects(RDF.type, PROV.Entity)) | set(
        graph.subjects(PROV.wasDerivedFrom, None)
    )
    return {"activity_count": len(activities), "lineage_depth": lineage_depth(graph, entities)}


def lineage_depth(graph: Graph, entities: set[URIRef] | None = None) -> int:
    """Return maximum prov:wasDerivedFrom path length."""
    entities = entities or {
        s for s in graph.subjects(PROV.wasDerivedFrom, None) if isinstance(s, URIRef)
    }

    def depth(node: URIRef, seen: frozenset[URIRef]) -> int:
        parents = [
            p
            for p in graph.objects(node, PROV.wasDerivedFrom)
            if isinstance(p, URIRef) and p not in seen
        ]
        if not parents:
            return 1
        return 1 + max(depth(parent, seen | {node}) for parent in parents)

    return max((depth(entity, frozenset()) for entity in entities), default=0)


def analytics_summary(
    settings: Settings | None = None, graph: Graph | None = None
) -> AnalyticsSummary:
    """Build the complete Phase 5 analytics summary."""
    settings = settings or load_settings()
    graph = graph or load_graph(settings=settings)
    ontology = ontology_statistics(graph)
    governance = governance_metrics(graph=graph, settings=settings)
    provenance = provenance_metrics(graph)
    run = run_reasoning(graph=graph, settings=settings)
    return AnalyticsSummary(
        node_count=len(_subjects_objects(graph)),
        edge_count=len(graph),
        graph_density=graph_density(graph),
        class_count=int(ontology["class_count"]),
        property_count=int(ontology["property_count"]),
        hierarchy_depth=int(ontology["hierarchy_depth"]),
        ownership_coverage=float(governance["ownership_coverage"]),
        steward_coverage=float(governance["steward_coverage"]),
        lineage_depth=int(provenance["lineage_depth"]),
        activity_count=int(provenance["activity_count"]),
        inferred_triples=run.inferred_count,
        inference_ratio=round(run.inferred_count / len(graph), 6) if len(graph) else 0.0,
    )

def orchestration_metrics(graph: Graph | None = None, settings: Settings | None = None) -> dict[str, int | float]:
    """Calculate Phase 7 orchestration and goal metrics."""
    settings = settings or load_settings()
    graph = graph or load_graph(settings=settings)
    orch = Namespace("https://example.org/semantic-platform/orchestration#")
    workflow_count = len(set(graph.subjects(RDF.type, orch.Workflow)))
    active_workflows = sum(
        1
        for workflow in set(graph.subjects(RDF.type, orch.Workflow))
        if str(graph.value(workflow, orch.lifecycleState, default="")) in {"Ready", "Running"}
    )
    dependency_count = len(list(graph.triples((None, orch.dependsOn, None))))
    approval_count = len(set(graph.subjects(RDF.type, orch.ApprovalGate)))
    event_count = len(set(graph.subjects(RDF.type, orch.Event)))
    execution_plan_count = len(set(graph.subjects(RDF.type, orch.ExecutionPlan)))
    goals = set(graph.subjects(RDF.type, orch.Goal))
    progresses = [float(graph.value(goal, orch.progress, default=0) or 0) for goal in goals]
    return {
        "workflow_count": workflow_count,
        "active_workflows": active_workflows,
        "dependency_count": dependency_count,
        "approval_count": approval_count,
        "event_count": event_count,
        "execution_plan_count": execution_plan_count,
        "goal_count": len(goals),
        "goal_completion": round(sum(progresses) / len(progresses), 4) if progresses else 0.0,
        "workflow_coverage": round(active_workflows / workflow_count, 4) if workflow_count else 0.0,
        "approval_bottlenecks": approval_count,
    }


def collaboration_metrics(graph: Graph | None = None, settings: Settings | None = None) -> dict[str, int | float]:
    """Calculate Phase 9 multi-agent collaboration metrics."""
    settings = settings or load_settings()
    graph = graph or load_graph(settings=settings)
    ma = Namespace("https://example.org/semantic-platform/multi-agent#")
    team_count = len(set(graph.subjects(RDF.type, ma.AgentTeam)))
    delegation_count = len(set(graph.subjects(RDF.type, ma.AgentDelegation)))
    active_conversations = len(set(graph.subjects(RDF.type, ma.AgentConversation)))
    negotiation_count = len(set(graph.subjects(RDF.type, ma.AgentNegotiation)))
    consensuses = set(graph.subjects(RDF.type, ma.AgentConsensus))
    conflicts = set(graph.subjects(RDF.type, ma.AgentConflict))
    approved_consensus = sum(1 for item in consensuses if str(graph.value(item, ma.consensusApproved, default="false")) == "true")
    unresolved_conflicts = sum(1 for item in conflicts if str(graph.value(item, ma.conflictStatus, default="Detected")) != "Resolved")
    tasks = set(graph.subjects(RDF.type, ma.AgentTask))
    completed_tasks = sum(1 for task in tasks if str(graph.value(task, ma.outcome, default="")) == "Completed")
    participating_agents = set(graph.objects(None, ma.delegatesTo)) | set(graph.objects(None, ma.agreedWith)) | set(graph.objects(None, ma.disagreedWith))
    return {
        "team_count": team_count,
        "delegation_count": delegation_count,
        "active_conversations": active_conversations,
        "negotiation_count": negotiation_count,
        "consensus_count": len(consensuses),
        "consensus_rate": round(approved_consensus / len(consensuses), 4) if consensuses else 0.0,
        "conflict_count": len(conflicts),
        "conflict_rate": round(unresolved_conflicts / max(delegation_count + negotiation_count + len(consensuses), 1), 4),
        "task_completion": round(completed_tasks / len(tasks), 4) if tasks else 0.0,
        "delegation_efficiency": round(delegation_count / max(team_count, 1), 4),
        "collaboration_participation": len(participating_agents),
    }
