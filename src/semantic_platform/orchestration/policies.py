"""Policy framework for policy-aware orchestration planning."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from semantic_platform.orchestration.common import ORCH, add_activity, add_label, bind, new_uri


@dataclass(frozen=True)
class PolicyDecision:
    """Result of evaluating an orchestration policy."""

    allowed: bool
    approvals_required: tuple[str, ...]
    constraints: tuple[str, ...]
    reason: str


class PolicyEvaluator:
    """Represent and evaluate orchestration, approval, escalation, and constraint policies."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def create_policy(self, label: str, *, requires_approval: bool = True, constraint: str = "human-controlled") -> URIRef:
        policy = new_uri("policy")
        self.graph.add((policy, RDF.type, ORCH.OrchestrationPolicy))
        self.graph.add((policy, ORCH.requiresApproval, Literal(requires_approval)))
        self.graph.add((policy, ORCH.executionConstraint, Literal(constraint)))
        add_label(self.graph, policy, label)
        add_activity(self.graph, ORCH.PolicyCreated, f"Created policy {label}", generated=policy)
        return policy

    def evaluate(self, workflow: str | URIRef) -> PolicyDecision:
        workflow_uri = URIRef(str(workflow))
        policies = list(self.graph.objects(workflow_uri, ORCH.governedByPolicy))
        approvals = []
        constraints = []
        for policy in policies:
            if str(self.graph.value(policy, ORCH.requiresApproval, default="false")).lower() == "true":
                approvals.append(str(policy))
            constraint = self.graph.value(policy, ORCH.executionConstraint)
            if constraint is not None:
                constraints.append(str(constraint))
        allowed = bool(policies)
        reason = "Policies found; execution may be planned only." if allowed else "Workflow has no policy reference."
        add_activity(self.graph, ORCH.PolicyEvaluated, reason, used=[workflow_uri, *[URIRef(str(p)) for p in policies]])
        return PolicyDecision(allowed, tuple(approvals), tuple(constraints), reason)
