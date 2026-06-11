"""Approval enforcement for execution actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.execution.common import EXEC, add_activity, bind, new_uri


@dataclass(frozen=True)
class ExecutionApproval:
    uri: str
    action: str
    approver: str
    status: str
    requested_by: str = ""


class ExecutionApprovalEngine:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def request(self, action: str | URIRef, requester: str, approver: str) -> ExecutionApproval:
        approval = new_uri("approval")
        action_uri = URIRef(str(action))
        self.graph.add((approval, RDF.type, EXEC.Approval))
        self.graph.add((approval, EXEC.approvesAction, action_uri))
        self.graph.add((approval, EXEC.requestedBy, Literal(requester)))
        self.graph.add((approval, EXEC.approver, Literal(approver)))
        self.graph.add((approval, EXEC.approvalStatus, Literal("Requested")))
        self.graph.add((approval, EXEC.requestedAt, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        self.graph.add((action_uri, EXEC.requiresApproval, approval))
        add_activity(self.graph, EXEC.ApprovalRequested, "Execution approval requested", used=[action_uri], generated=approval)
        return self.get(approval)

    def approve(self, approval: str | URIRef, approver: str, comment: str = "") -> ExecutionApproval:
        approval_uri = URIRef(str(approval))
        self.graph.set((approval_uri, EXEC.approver, Literal(approver)))
        self.graph.set((approval_uri, EXEC.approvalStatus, Literal("Approved")))
        self.graph.set((approval_uri, EXEC.reviewComment, Literal(comment)))
        self.graph.set((approval_uri, EXEC.reviewedAt, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        add_activity(self.graph, EXEC.ApprovalGranted, "Execution approval granted", used=[approval_uri])
        return self.get(approval_uri)

    def approved_count(self, action: str | URIRef) -> int:
        action_uri = URIRef(str(action))
        return sum(
            1
            for approval in self.graph.objects(action_uri, EXEC.requiresApproval)
            if str(self.graph.value(approval, EXEC.approvalStatus, default="")) == "Approved"
        )

    def authorized(self, action: str | URIRef, required: int) -> bool:
        return self.approved_count(action) >= required

    def get(self, approval: str | URIRef) -> ExecutionApproval:
        approval_uri = URIRef(str(approval))
        return ExecutionApproval(
            str(approval_uri),
            str(self.graph.value(approval_uri, EXEC.approvesAction, default="")),
            str(self.graph.value(approval_uri, EXEC.approver, default="")),
            str(self.graph.value(approval_uri, EXEC.approvalStatus, default="")),
            str(self.graph.value(approval_uri, EXEC.requestedBy, default="")),
        )

    def list_approvals(self) -> list[ExecutionApproval]:
        return [self.get(a) for a in self.graph.subjects(RDF.type, EXEC.Approval)]
