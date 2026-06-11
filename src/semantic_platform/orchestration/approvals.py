"""Human-in-the-loop approval framework."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.orchestration.common import ORCH, add_activity, bind, new_uri


@dataclass(frozen=True)
class ApprovalRequest:
    """Approval request lifecycle record."""

    uri: str
    subject: str
    requester: str
    reviewer: str
    status: str


class ApprovalWorkflow:
    """Request, review, and approve orchestration recommendations."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def request(self, subject: str | URIRef, requester: str, reviewer: str) -> ApprovalRequest:
        approval = new_uri("approval")
        subject_uri = URIRef(str(subject))
        self.graph.add((approval, RDF.type, ORCH.ApprovalGate))
        self.graph.add((approval, ORCH.approvalSubject, subject_uri))
        self.graph.add((approval, ORCH.requestedBy, Literal(requester)))
        self.graph.add((approval, ORCH.reviewedBy, Literal(reviewer)))
        self.graph.add((approval, ORCH.approvalStatus, Literal("Requested")))
        self.graph.add((approval, ORCH.requestedAt, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        self.graph.add((subject_uri, ORCH.requiresApproval, approval))
        add_activity(self.graph, ORCH.ApprovalRequested, "Requested approval", used=[subject_uri], generated=approval)
        return self._record(approval)

    def review(self, approval: str | URIRef, reviewer: str, decision: str, comment: str = "") -> ApprovalRequest:
        approval_uri = URIRef(str(approval))
        self.graph.set((approval_uri, ORCH.reviewedBy, Literal(reviewer)))
        self.graph.set((approval_uri, ORCH.approvalStatus, Literal(decision)))
        self.graph.set((approval_uri, ORCH.reviewComment, Literal(comment)))
        self.graph.set((approval_uri, ORCH.reviewedAt, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        add_activity(self.graph, ORCH.ApprovalReviewed, f"Approval {decision}", used=[approval_uri])
        return self._record(approval_uri)

    def _record(self, approval: URIRef) -> ApprovalRequest:
        return ApprovalRequest(
            str(approval),
            str(self.graph.value(approval, ORCH.approvalSubject, default="")),
            str(self.graph.value(approval, ORCH.requestedBy, default="")),
            str(self.graph.value(approval, ORCH.reviewedBy, default="")),
            str(self.graph.value(approval, ORCH.approvalStatus, default="")),
        )
