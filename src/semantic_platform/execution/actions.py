"""Semantic action and target models for generic execution targets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.execution.common import EXEC, add_label, bind, new_uri, text
from semantic_platform.execution.risk import RiskLevel


@dataclass(frozen=True)
class ExecutionTargetRecord:
    uri: str
    label: str
    target_type: str
    endpoint: str = ""


@dataclass(frozen=True)
class ExecutionActionRecord:
    uri: str
    label: str
    action_type: str
    target: str
    risk: str
    rollback_supported: bool
    status: str = "Draft"
    approval_required: int = 0


@dataclass(frozen=True)
class TargetResponse:
    success: bool
    status_code: int
    message: str
    payload: dict[str, object] = field(default_factory=dict)


class ExecutionTarget(Protocol):
    target_type: str

    def execute(self, action: ExecutionActionRecord, payload: dict[str, object]) -> TargetResponse: ...

    def rollback(self, action: ExecutionActionRecord, payload: dict[str, object]) -> TargetResponse: ...


class GenericTarget:
    """Safe generic target adapter used by REST, webhook, queue, DB, file, and email targets."""

    def __init__(self, target_type: str) -> None:
        self.target_type = target_type

    def execute(self, action: ExecutionActionRecord, payload: dict[str, object]) -> TargetResponse:
        return TargetResponse(True, 202, f"{action.action_type} accepted by {self.target_type}", {"echo": payload})

    def rollback(self, action: ExecutionActionRecord, payload: dict[str, object]) -> TargetResponse:
        if not action.rollback_supported:
            return TargetResponse(False, 409, "Rollback not supported", {"echo": payload})
        return TargetResponse(True, 200, f"Rollback accepted by {self.target_type}", {"echo": payload})


TARGET_TYPES = {
    "REST API": GenericTarget("REST API"),
    "Webhook": GenericTarget("Webhook"),
    "Message Queue": GenericTarget("Message Queue"),
    "Database Procedure": GenericTarget("Database Procedure"),
    "File Drop": GenericTarget("File Drop"),
    "Email": GenericTarget("Email"),
}


class ActionCatalog:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def create_target(self, label: str, target_type: str, endpoint: str = "") -> ExecutionTargetRecord:
        if target_type not in TARGET_TYPES:
            raise ValueError(f"unsupported target type: {target_type}")
        target = new_uri("target")
        self.graph.add((target, RDF.type, EXEC.ExecutionTarget))
        self.graph.add((target, EXEC.targetType, Literal(target_type)))
        self.graph.add((target, EXEC.endpoint, Literal(endpoint)))
        add_label(self.graph, target, label)
        return self.get_target(target)

    def create_action(
        self,
        label: str,
        action_type: str,
        target: str | URIRef,
        *,
        risk: RiskLevel = RiskLevel.LOW,
        rollback_supported: bool = True,
        status: str = "Draft",
        approval_required: int = 0,
    ) -> ExecutionActionRecord:
        action = new_uri("action")
        target_uri = URIRef(str(target))
        self.graph.add((action, RDF.type, EXEC.ExecutionAction))
        self.graph.add((action, EXEC.actionType, Literal(action_type)))
        self.graph.add((action, EXEC.executesAgainst, target_uri))
        self.graph.add((action, EXEC.riskLevel, Literal(risk.value)))
        self.graph.add((action, EXEC.rollbackSupported, Literal(rollback_supported, datatype=XSD.boolean)))
        self.graph.add((action, EXEC.registryStatus, Literal(status)))
        self.graph.add((action, EXEC.approvalCountRequired, Literal(approval_required, datatype=XSD.integer)))
        add_label(self.graph, action, label)
        return self.get_action(action)

    def get_target(self, target: str | URIRef) -> ExecutionTargetRecord:
        target_uri = URIRef(str(target))
        return ExecutionTargetRecord(
            str(target_uri),
            text(self.graph, target_uri, EXEC.label) or text(self.graph, target_uri, URIRef("http://www.w3.org/2000/01/rdf-schema#label")),
            text(self.graph, target_uri, EXEC.targetType),
            text(self.graph, target_uri, EXEC.endpoint),
        )

    def get_action(self, action: str | URIRef) -> ExecutionActionRecord:
        action_uri = URIRef(str(action))
        target = self.graph.value(action_uri, EXEC.executesAgainst)
        return ExecutionActionRecord(
            str(action_uri),
            text(self.graph, action_uri, URIRef("http://www.w3.org/2000/01/rdf-schema#label")),
            text(self.graph, action_uri, EXEC.actionType),
            str(target) if target else "",
            text(self.graph, action_uri, EXEC.riskLevel, RiskLevel.LOW.value),
            text(self.graph, action_uri, EXEC.rollbackSupported, "false").lower() == "true",
            text(self.graph, action_uri, EXEC.registryStatus, "Draft"),
            int(text(self.graph, action_uri, EXEC.approvalCountRequired, "0")),
        )

    def list_actions(self) -> list[ExecutionActionRecord]:
        return [self.get_action(action) for action in self.graph.subjects(RDF.type, EXEC.ExecutionAction)]
