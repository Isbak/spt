"""Policy enforcement for governed execution."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.execution.actions import ExecutionActionRecord
from semantic_platform.execution.common import EXEC, add_label, bind, new_uri
from semantic_platform.execution.risk import RiskClassifier, RiskLevel


@dataclass(frozen=True)
class ExecutionPolicyDecision:
    allowed: bool
    required_approvals: int
    reason: str


class ExecutionPolicyEngine:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())
        self.risk = RiskClassifier()

    def create_policy(
        self,
        label: str,
        *,
        max_risk: RiskLevel = RiskLevel.HIGH,
        allowed_targets: tuple[str, ...] = ("REST API", "Webhook", "Message Queue", "Database Procedure", "File Drop", "Email"),
        allowed_actions: tuple[str, ...] = ("Create Resource", "Update Resource", "Delete Resource", "Publish Message", "Send Notification", "Start Process", "Stop Process", "Generate Artifact"),
        require_approval: bool = True,
    ) -> URIRef:
        policy = new_uri("policy")
        self.graph.add((policy, RDF.type, EXEC.ExecutionPolicy))
        self.graph.add((policy, EXEC.maxRiskLevel, Literal(max_risk.value)))
        self.graph.add((policy, EXEC.requireApproval, Literal(require_approval, datatype=XSD.boolean)))
        for target in allowed_targets:
            self.graph.add((policy, EXEC.allowedTargetType, Literal(target)))
        for action in allowed_actions:
            self.graph.add((policy, EXEC.allowedActionType, Literal(action)))
        add_label(self.graph, policy, label)
        return policy

    def evaluate(self, action: ExecutionActionRecord, target_type: str, policy: str | URIRef | None = None) -> ExecutionPolicyDecision:
        policies = [URIRef(str(policy))] if policy else list(self.graph.subjects(RDF.type, EXEC.ExecutionPolicy))
        if not policies:
            return ExecutionPolicyDecision(False, 0, "No execution policy is assigned.")
        reasons = []
        for policy_uri in policies:
            allowed_actions = {str(v) for v in self.graph.objects(policy_uri, EXEC.allowedActionType)}
            allowed_targets = {str(v) for v in self.graph.objects(policy_uri, EXEC.allowedTargetType)}
            max_risk = RiskLevel(str(self.graph.value(policy_uri, EXEC.maxRiskLevel, default=RiskLevel.LOW.value)))
            if allowed_actions and action.action_type not in allowed_actions:
                reasons.append(f"Action type {action.action_type} is not allowed")
                continue
            if allowed_targets and target_type not in allowed_targets:
                reasons.append(f"Target type {target_type} is not allowed")
                continue
            if not self.risk.allowed_at_or_below(RiskLevel(action.risk), max_risk):
                reasons.append(f"Risk {action.risk} exceeds threshold {max_risk.value}")
                continue
            risk_decision = self.risk.classify(action.action_type, target_type, action.risk)
            required = max(action.approval_required, risk_decision.approvals_required)
            if str(self.graph.value(policy_uri, EXEC.requireApproval, default="true")).lower() != "true":
                required = action.approval_required
            return ExecutionPolicyDecision(True, required, "Execution policy allows action.")
        return ExecutionPolicyDecision(False, 0, "; ".join(reasons) or "Execution policy denied action.")
