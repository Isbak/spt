"""Execution outcome records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.execution.common import EXEC, add_activity, bind, new_uri


@dataclass(frozen=True)
class ExecutionOutcomeRecord:
    uri: str
    execution: str
    status: str
    message: str
    verified: bool = False


class OutcomeStore:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def create(self, execution: str | URIRef, status: str, message: str) -> ExecutionOutcomeRecord:
        execution_uri = URIRef(str(execution))
        outcome = new_uri("outcome")
        self.graph.add((outcome, RDF.type, EXEC.ExecutionOutcome))
        self.graph.add((outcome, EXEC.outcomeStatus, Literal(status)))
        self.graph.add((outcome, EXEC.outcomeMessage, Literal(message)))
        self.graph.add((outcome, EXEC.outcomeTime, Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime)))
        self.graph.add((execution_uri, EXEC.producedOutcome, outcome))
        add_activity(self.graph, EXEC.OutcomeRecorded, "Execution outcome recorded", used=[execution_uri], generated=outcome)
        return self.get(outcome)

    def mark_verified(self, outcome: str | URIRef, verified: bool) -> ExecutionOutcomeRecord:
        self.graph.set((URIRef(str(outcome)), EXEC.verified, Literal(verified, datatype=XSD.boolean)))
        return self.get(outcome)

    def get(self, outcome: str | URIRef) -> ExecutionOutcomeRecord:
        outcome_uri = URIRef(str(outcome))
        execution = next((str(s) for s in self.graph.subjects(EXEC.producedOutcome, outcome_uri)), "")
        return ExecutionOutcomeRecord(
            str(outcome_uri),
            execution,
            str(self.graph.value(outcome_uri, EXEC.outcomeStatus, default="")),
            str(self.graph.value(outcome_uri, EXEC.outcomeMessage, default="")),
            str(self.graph.value(outcome_uri, EXEC.verified, default="false")).lower() == "true",
        )

    def list_outcomes(self) -> list[ExecutionOutcomeRecord]:
        return [self.get(o) for o in self.graph.subjects(RDF.type, EXEC.ExecutionOutcome)]
