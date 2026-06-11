"""Semantic workflow model and validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from semantic_platform.orchestration.common import AGGOV, ORCH, add_activity, add_label, bind, new_uri, text


class WorkflowState(StrEnum):
    """Modeled workflow states; no execution is performed in Phase 7."""

    DRAFT = "Draft"
    READY = "Ready"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


@dataclass(frozen=True)
class WorkflowDefinition:
    """Workflow resource with tasks and dependencies."""

    uri: str
    label: str
    state: WorkflowState
    tasks: tuple[str, ...]
    dependencies: tuple[tuple[str, str], ...]


class WorkflowEngine:
    """Create, inspect, and validate semantic workflow definitions."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def define_workflow(
        self,
        label: str,
        tasks: list[str],
        *,
        owner: str = "platform-owner",
        steward: str = "platform-steward",
        version: str = "1.0.0",
        policy: str | URIRef = ORCH.defaultOrchestrationPolicy,
        state: WorkflowState = WorkflowState.DRAFT,
    ) -> WorkflowDefinition:
        """Define a governed workflow and its tasks."""
        workflow = new_uri("workflow")
        self.graph.add((workflow, RDF.type, ORCH.Workflow))
        add_label(self.graph, workflow, label)
        self.graph.add((workflow, AGGOV.owner, Literal(owner)))
        self.graph.add((workflow, AGGOV.steward, Literal(steward)))
        self.graph.add((workflow, OWL.versionInfo, Literal(version)))
        self.graph.add((workflow, AGGOV.approvalStatus, Literal("Draft")))
        self.graph.add((workflow, ORCH.lifecycleState, Literal(state.value)))
        self.graph.add((workflow, ORCH.governedByPolicy, URIRef(str(policy))))
        for task_label in tasks:
            task = new_uri("task")
            self.graph.add((task, RDF.type, ORCH.Task))
            add_label(self.graph, task, task_label)
            self.graph.add((workflow, ORCH.decomposesInto, task))
        add_activity(self.graph, ORCH.WorkflowDefined, f"Defined workflow {label}", generated=workflow)
        return self.get_workflow(workflow)

    def add_dependency(self, task: str | URIRef, depends_on: str | URIRef) -> None:
        """Model a task dependency."""
        self.graph.add((URIRef(str(task)), ORCH.dependsOn, URIRef(str(depends_on))))
        add_activity(self.graph, ORCH.DependencyRegistered, "Registered workflow dependency", used=[URIRef(str(task)), URIRef(str(depends_on))])

    def dependency_graph(self, workflow: str | URIRef) -> dict[str, set[str]]:
        """Return dependency adjacency for workflow tasks."""
        workflow_uri = URIRef(str(workflow))
        tasks = [URIRef(str(t)) for t in self.graph.objects(workflow_uri, ORCH.decomposesInto)]
        return {str(task): {str(dep) for dep in self.graph.objects(task, ORCH.dependsOn)} for task in tasks}

    def validate_workflow(self, workflow: str | URIRef) -> list[str]:
        """Validate governance metadata and dependency consistency."""
        workflow_uri = URIRef(str(workflow))
        errors: list[str] = []
        for pred, name in [(AGGOV.owner, "owner"), (AGGOV.steward, "steward"), (OWL.versionInfo, "version"), (AGGOV.approvalStatus, "approval status"), (ORCH.governedByPolicy, "policy")]:
            if self.graph.value(workflow_uri, pred) is None:
                errors.append(f"workflow missing {name}")
        state = text(self.graph, workflow_uri, ORCH.lifecycleState, WorkflowState.DRAFT.value)
        if state not in {s.value for s in WorkflowState}:
            errors.append(f"unsupported workflow state {state}")
        tasks = set(self.graph.objects(workflow_uri, ORCH.decomposesInto))
        for task in tasks:
            for dependency in self.graph.objects(task, ORCH.dependsOn):
                if dependency not in tasks:
                    errors.append(f"dependency {dependency} is not in workflow")
        if self._has_cycle(self.dependency_graph(workflow_uri)):
            errors.append("workflow dependency cycle detected")
        return errors

    def _has_cycle(self, graph: dict[str, set[str]]) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            if any(visit(dep) for dep in graph.get(node, set())):
                return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in graph)

    def get_workflow(self, workflow: str | URIRef) -> WorkflowDefinition:
        """Return a workflow definition record."""
        workflow_uri = URIRef(str(workflow))
        state = WorkflowState(text(self.graph, workflow_uri, ORCH.lifecycleState, WorkflowState.DRAFT.value))
        dependencies = tuple(
            (str(task), str(dep))
            for task in self.graph.objects(workflow_uri, ORCH.decomposesInto)
            for dep in self.graph.objects(task, ORCH.dependsOn)
        )
        return WorkflowDefinition(
            uri=str(workflow_uri),
            label=text(self.graph, workflow_uri, RDFS.label),
            state=state,
            tasks=tuple(str(t) for t in self.graph.objects(workflow_uri, ORCH.decomposesInto)),
            dependencies=dependencies,
        )
