"""Governed execution service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, XSD

from semantic_platform.execution.actions import ActionCatalog, TARGET_TYPES
from semantic_platform.execution.approvals import ExecutionApprovalEngine
from semantic_platform.execution.common import EXEC, add_activity, bind, new_uri
from semantic_platform.execution.explainability import ExecutionExplainer
from semantic_platform.execution.outcomes import OutcomeStore
from semantic_platform.execution.policies import ExecutionPolicyEngine
from semantic_platform.execution.verification import VerificationService


@dataclass(frozen=True)
class ExecutionRecord:
    uri: str
    action: str
    target: str
    status: str
    outcome: str


class GovernedExecutor:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())
        self.catalog = ActionCatalog(self.graph)
        self.policies = ExecutionPolicyEngine(self.graph)
        self.approvals = ExecutionApprovalEngine(self.graph)
        self.outcomes = OutcomeStore(self.graph)
        self.verifier = VerificationService(self.graph)

    def execute(
        self,
        action: str | URIRef,
        *,
        payload: dict[str, object] | None = None,
        executor: str = "semantic-execution-agent",
        policy: str | URIRef | None = None,
        goal: str | URIRef | None = None,
        workflow: str | URIRef | None = None,
        plan: str | URIRef | None = None,
    ) -> ExecutionRecord:
        action_record = self.catalog.get_action(action)
        target_record = self.catalog.get_target(action_record.target)
        decision = self.policies.evaluate(action_record, target_record.target_type, policy)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if not self.approvals.authorized(action_record.uri, decision.required_approvals):
            raise PermissionError(f"Execution requires {decision.required_approvals} approval(s).")
        adapter = TARGET_TYPES[target_record.target_type]
        execution = new_uri("execution")
        self.graph.add((execution, RDF.type, EXEC.ExecutionTask))
        self.graph.add((execution, EXEC.executedAction, URIRef(action_record.uri)))
        self.graph.add((execution, EXEC.executesAgainst, URIRef(target_record.uri)))
        self.graph.add((execution, EXEC.executedByAgent, Literal(executor)))
        self.graph.add((execution, EXEC.executionTime, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        if policy:
            self.graph.add((execution, EXEC.governedBy, URIRef(str(policy))))
        for predicate, value in ((EXEC.forGoal, goal), (EXEC.forWorkflow, workflow), (EXEC.forExecutionPlan, plan)):
            if value:
                self.graph.add((execution, predicate, URIRef(str(value))))
        response = adapter.execute(action_record, payload or {})
        outcome = self.outcomes.create(execution, "Succeeded" if response.success else "Failed", response.message)
        self.verifier.verify(outcome.uri)
        self.graph.add((execution, PROV.wasAssociatedWith, URIRef(EXEC[executor])))
        add_activity(self.graph, EXEC.ActionExecuted, "Governed action executed", actor=executor, used=[URIRef(action_record.uri)], generated=execution)
        ExecutionExplainer(self.graph).explain(execution)
        return self.get(execution)

    def get(self, execution: str | URIRef) -> ExecutionRecord:
        execution_uri = URIRef(str(execution))
        action = str(self.graph.value(execution_uri, EXEC.executedAction, default=""))
        target = str(self.graph.value(execution_uri, EXEC.executesAgainst, default=""))
        outcome = str(self.graph.value(execution_uri, EXEC.producedOutcome, default=""))
        status = str(self.graph.value(URIRef(outcome), EXEC.outcomeStatus, default="")) if outcome else ""
        return ExecutionRecord(str(execution_uri), action, target, status, outcome)

    def list_executions(self) -> list[ExecutionRecord]:
        return [self.get(e) for e in self.graph.subjects(RDF.type, EXEC.ExecutionTask)]
