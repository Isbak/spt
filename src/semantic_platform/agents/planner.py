"""Non-autonomous agent planning support."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from semantic_platform.agents.registry import AGENT, AgentRecord


@dataclass(frozen=True)
class AgentPlan:
    """A proposed plan with tasks and actions; not an executable workflow."""

    plan_id: str
    goal: str
    tasks: tuple[str, ...]
    actions: tuple[str, ...]


class AgentPlanner:
    """Create plans only; this class intentionally never executes actions."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph or Graph()

    def plan(self, agent: AgentRecord, goal: str, tasks: list[str]) -> AgentPlan:
        """Create a task/action plan for human review."""
        plan_uri = URIRef(AGENT[f"plan-{uuid4()}"])
        actions = tuple(f"Review task: {task}" for task in tasks)
        self.graph.add((plan_uri, RDF.type, AGENT.AgentPlan))
        self.graph.add((plan_uri, RDFS.label, Literal(goal)))
        self.graph.add((URIRef(agent.uri), AGENT.executedPlan, plan_uri))
        for task in tasks:
            self.graph.add((plan_uri, AGENT.hasTask, Literal(task)))
        for action in actions:
            self.graph.add((plan_uri, AGENT.hasAction, Literal(action)))
        return AgentPlan(str(plan_uri), goal, tuple(tasks), actions)
