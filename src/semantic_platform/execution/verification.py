"""Verification framework for execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.execution.common import EXEC, add_activity, bind, new_uri
from semantic_platform.execution.outcomes import OutcomeStore


@dataclass(frozen=True)
class VerificationRecord:
    uri: str
    outcome: str
    passed: bool
    message: str


class VerificationService:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def verify(self, outcome: str | URIRef, expected_status: str = "Succeeded") -> VerificationRecord:
        outcome_uri = URIRef(str(outcome))
        actual = str(self.graph.value(outcome_uri, EXEC.outcomeStatus, default=""))
        passed = actual == expected_status
        verification = new_uri("verification")
        self.graph.add((verification, RDF.type, EXEC.VerificationActivity))
        self.graph.add((verification, EXEC.verifiesOutcome, outcome_uri))
        self.graph.add((verification, EXEC.verificationPassed, Literal(passed, datatype=XSD.boolean)))
        self.graph.add((verification, EXEC.verificationMessage, Literal("Expected outcome achieved" if passed else f"Expected {expected_status}, got {actual}")))
        self.graph.add((verification, EXEC.verifiedAt, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        self.graph.add((outcome_uri, EXEC.verifiedBy, verification))
        OutcomeStore(self.graph).mark_verified(outcome_uri, passed)
        add_activity(self.graph, EXEC.ExecutionVerified, "Execution outcome verified", used=[outcome_uri], generated=verification)
        return self.get(verification)

    def get(self, verification: str | URIRef) -> VerificationRecord:
        uri = URIRef(str(verification))
        return VerificationRecord(
            str(uri),
            str(self.graph.value(uri, EXEC.verifiesOutcome, default="")),
            str(self.graph.value(uri, EXEC.verificationPassed, default="false")).lower() == "true",
            str(self.graph.value(uri, EXEC.verificationMessage, default="")),
        )

    def list_verifications(self) -> list[VerificationRecord]:
        return [self.get(v) for v in self.graph.subjects(RDF.type, EXEC.VerificationActivity)]
