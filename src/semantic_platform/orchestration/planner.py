"""Policy-aware orchestration planner facade."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef

from semantic_platform.orchestration.execution_plan import ExecutionPlan, ExecutionPlanBuilder
from semantic_platform.orchestration.policies import PolicyDecision, PolicyEvaluator


@dataclass(frozen=True)
class PlanningResult:
    """Combined execution plan and policy decision."""

    plan: ExecutionPlan
    policy_decision: PolicyDecision


class OrchestrationPlanner:
    """Create explainable plans only; never executes business actions."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        self.builder = ExecutionPlanBuilder(self.graph)
        self.policies = PolicyEvaluator(self.graph)

    def propose_plan(self, goal: str | URIRef, workflow: str | URIRef, tasks: list[str | URIRef]) -> PlanningResult:
        decision = self.policies.evaluate(workflow)
        plan = self.builder.build_plan(goal, tasks)
        return PlanningResult(plan, decision)
