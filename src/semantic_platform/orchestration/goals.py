"""Goal and objective management represented as RDF resources."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, XSD

from semantic_platform.orchestration.common import ORCH, add_activity, add_label, bind, new_uri, text


@dataclass(frozen=True)
class GoalRecord:
    """Semantic goal with objective and task progress metadata."""

    uri: str
    label: str
    objectives: tuple[str, ...]
    tasks: tuple[str, ...]
    progress: float


class GoalManager:
    """Create goals, register objectives, map tasks, and evaluate progress."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def create_goal(self, label: str, *, status: str = "Active", owner: str = "platform") -> GoalRecord:
        """Create a governed RDF goal resource."""
        goal = new_uri("goal")
        self.graph.add((goal, RDF.type, ORCH.Goal))
        self.graph.add((goal, ORCH.status, Literal(status)))
        self.graph.add((goal, DCTERMS.creator, Literal(owner)))
        add_label(self.graph, goal, label)
        add_activity(self.graph, ORCH.GoalCreated, f"Created goal {label}", used=[], generated=goal)
        return self.get_goal(goal)

    def register_objective(self, goal: str | URIRef, label: str) -> URIRef:
        """Create an objective and connect it to a goal."""
        goal_uri = URIRef(str(goal))
        objective = new_uri("objective")
        self.graph.add((objective, RDF.type, ORCH.Objective))
        add_label(self.graph, objective, label)
        self.graph.add((goal_uri, ORCH.hasObjective, objective))
        self.graph.add((objective, ORCH.contributesToGoal, goal_uri))
        add_activity(self.graph, ORCH.ObjectiveRegistered, f"Registered objective {label}", used=[goal_uri], generated=objective)
        return objective

    def map_task_to_goal(self, task: str | URIRef, goal: str | URIRef, *, complete: bool = False) -> None:
        """Map a task to a goal and optionally mark it complete."""
        task_uri = URIRef(str(task))
        goal_uri = URIRef(str(goal))
        self.graph.add((task_uri, RDF.type, ORCH.Task))
        self.graph.add((task_uri, ORCH.contributesToGoal, goal_uri))
        self.graph.add((goal_uri, ORCH.hasTask, task_uri))
        self.graph.set((task_uri, ORCH.completed, Literal(complete, datatype=XSD.boolean)))
        add_activity(self.graph, ORCH.GoalTaskMapped, "Mapped task to goal", used=[task_uri, goal_uri])

    def evaluate_progress(self, goal: str | URIRef) -> float:
        """Return completion ratio for tasks mapped to a goal."""
        goal_uri = URIRef(str(goal))
        tasks = list(self.graph.objects(goal_uri, ORCH.hasTask))
        if not tasks:
            return 0.0
        complete = sum(1 for task in tasks if str(self.graph.value(task, ORCH.completed)).lower() == "true")
        progress = round(complete / len(tasks), 4)
        self.graph.set((goal_uri, ORCH.progress, Literal(progress, datatype=XSD.decimal)))
        return progress

    def get_goal(self, goal: str | URIRef) -> GoalRecord:
        """Return a goal record from RDF."""
        goal_uri = URIRef(str(goal))
        progress = self.evaluate_progress(goal_uri) if (goal_uri, ORCH.hasTask, None) in self.graph else 0.0
        return GoalRecord(
            uri=str(goal_uri),
            label=text(self.graph, goal_uri, RDFS.label),
            objectives=tuple(str(o) for o in self.graph.objects(goal_uri, ORCH.hasObjective)),
            tasks=tuple(str(t) for t in self.graph.objects(goal_uri, ORCH.hasTask)),
            progress=progress,
        )
