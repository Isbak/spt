"""Distributed planning helpers for collaborative agent work."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS

from semantic_platform.multi_agent.common import MA, add_prov_activity, bind, now_literal


@dataclass(frozen=True)
class CollaborativePlan:
    uri: str
    goal: str
    tasks: tuple[str, ...]
    agents: tuple[str, ...]


class CollaborationService:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def plan(self, goal: str, assignments: dict[str, str], *, actor: str = "orchestrator-agent") -> CollaborativePlan:
        plan = URIRef(MA[f"collaborative-plan-{len(list(self.graph.subjects(RDF.type, MA.CollaborativePlan))) + 1}"])
        goal_uri = URIRef(goal) if goal.startswith("http") else URIRef(MA[goal])
        self.graph.add((plan, RDF.type, MA.CollaborativePlan))
        self.graph.add((plan, RDFS.label, Literal("Collaborative plan")))
        self.graph.add((plan, PROV.wasDerivedFrom, goal_uri))
        self.graph.add((plan, PROV.generatedAtTime, now_literal()))
        for task, agent in assignments.items():
            task_uri = URIRef(task) if task.startswith("http") else URIRef(MA[task])
            agent_uri = URIRef(agent) if agent.startswith("http") else URIRef(MA[agent])
            self.graph.add((plan, MA.contributedTo, task_uri))
            self.graph.add((task_uri, MA.assignedTask, agent_uri))
        add_prov_activity(self.graph, MA.CollaborationActivity, "Create collaborative distributed plan", actor, generated=plan)
        return CollaborativePlan(str(plan), str(goal_uri), tuple(assignments), tuple(assignments.values()))
