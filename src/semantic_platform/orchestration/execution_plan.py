"""Explainable execution-plan generation without autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.orchestration.common import ORCH, add_activity, add_label, bind, new_uri


@dataclass(frozen=True)
class ExecutionPlan:
    """Ordered, explainable plan for human review."""

    uri: str
    goal: str
    tasks: tuple[str, ...]
    explanation: str
    ready: bool


class ExecutionPlanBuilder:
    """Build topologically ordered plans from goals, tasks, and dependencies."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def build_plan(self, goal: str | URIRef, tasks: list[str | URIRef]) -> ExecutionPlan:
        """Create an execution plan resource and keep it non-executable."""
        goal_uri = URIRef(str(goal))
        task_uris = [URIRef(str(task)) for task in tasks]
        ordered = self.order_tasks(task_uris)
        plan = new_uri("execution-plan")
        self.graph.add((plan, RDF.type, ORCH.ExecutionPlan))
        self.graph.add((plan, ORCH.contributesToGoal, goal_uri))
        self.graph.add((plan, ORCH.planVersion, Literal("1.0.0")))
        self.graph.add((plan, ORCH.executionReady, Literal(False, datatype=XSD.boolean)))
        for index, task in enumerate(ordered, start=1):
            self.graph.add((task, RDF.type, ORCH.Task))
            self.graph.add((plan, ORCH.hasPlannedTask, task))
            self.graph.add((task, ORCH.planOrder, Literal(index, datatype=XSD.integer)))
        explanation = f"Plan orders {len(ordered)} tasks after dependency analysis; execution is disabled pending human approval."
        self.graph.add((plan, ORCH.explanationText, Literal(explanation)))
        add_label(self.graph, plan, "Explainable execution plan")
        add_activity(self.graph, ORCH.ExecutionPlanGenerated, "Generated execution plan", used=[goal_uri, *task_uris], generated=plan)
        return ExecutionPlan(str(plan), str(goal_uri), tuple(str(t) for t in ordered), explanation, False)

    def order_tasks(self, tasks: list[URIRef]) -> list[URIRef]:
        """Topologically order tasks by ``orch:dependsOn``."""
        task_set = set(tasks)
        ordered: list[URIRef] = []
        temporary: set[URIRef] = set()
        permanent: set[URIRef] = set()

        def visit(task: URIRef) -> None:
            if task in permanent:
                return
            if task in temporary:
                raise ValueError("dependency cycle detected")
            temporary.add(task)
            for dep in self.graph.objects(task, ORCH.dependsOn):
                dep_uri = URIRef(str(dep))
                if dep_uri in task_set:
                    visit(dep_uri)
            temporary.remove(task)
            permanent.add(task)
            ordered.append(task)

        for task in sorted(task_set, key=str):
            visit(task)
        return ordered
