"""Rollback plan and execution framework."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.execution.actions import ActionCatalog, TARGET_TYPES
from semantic_platform.execution.common import EXEC, add_activity, bind, new_uri
from semantic_platform.execution.outcomes import ExecutionOutcomeRecord, OutcomeStore
from semantic_platform.execution.verification import VerificationService


@dataclass(frozen=True)
class RollbackPlanRecord:
    uri: str
    action: str
    supported: bool
    description: str


class RollbackService:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def declare_plan(self, action: str | URIRef, supported: bool, description: str) -> RollbackPlanRecord:
        action_uri = URIRef(str(action))
        plan = new_uri("rollback")
        self.graph.add((plan, RDF.type, EXEC.RollbackPlan))
        self.graph.add((plan, EXEC.rollbackSupported, Literal(supported, datatype=XSD.boolean)))
        self.graph.add((plan, EXEC.rollbackDescription, Literal(description)))
        self.graph.add((action_uri, EXEC.hasRollbackPlan, plan))
        add_activity(self.graph, EXEC.RollbackPlanDeclared, "Rollback plan declared", used=[action_uri], generated=plan)
        return self.get(plan)

    def rollback(self, execution: str | URIRef, action: str | URIRef, payload: dict[str, object] | None = None) -> ExecutionOutcomeRecord:
        catalog = ActionCatalog(self.graph)
        action_record = catalog.get_action(action)
        target_record = catalog.get_target(action_record.target)
        adapter = TARGET_TYPES[target_record.target_type]
        response = adapter.rollback(action_record, payload or {})
        outcome = OutcomeStore(self.graph).create(execution, "RolledBack" if response.success else "RollbackFailed", response.message)
        VerificationService(self.graph).verify(outcome.uri, expected_status="RolledBack" if response.success else "RolledBack")
        add_activity(self.graph, EXEC.RollbackExecuted, "Rollback executed", used=[URIRef(str(execution)), URIRef(str(action))], generated=URIRef(outcome.uri))
        return outcome

    def get(self, plan: str | URIRef) -> RollbackPlanRecord:
        plan_uri = URIRef(str(plan))
        action = next((str(s) for s in self.graph.subjects(EXEC.hasRollbackPlan, plan_uri)), "")
        return RollbackPlanRecord(
            str(plan_uri),
            action,
            str(self.graph.value(plan_uri, EXEC.rollbackSupported, default="false")).lower() == "true",
            str(self.graph.value(plan_uri, EXEC.rollbackDescription, default="")),
        )

    def list_plans(self) -> list[RollbackPlanRecord]:
        return [self.get(p) for p in self.graph.subjects(RDF.type, EXEC.RollbackPlan)]
