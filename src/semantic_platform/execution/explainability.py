"""Explainable execution traces for human auditability."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from semantic_platform.execution.common import EXEC, add_activity, bind, new_uri


@dataclass(frozen=True)
class ExecutionExplanation:
    uri: str
    execution: str
    text: str


class ExecutionExplainer:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def explain(self, execution: str | URIRef) -> ExecutionExplanation:
        execution_uri = URIRef(str(execution))
        action = str(self.graph.value(execution_uri, EXEC.executedAction, default=""))
        policy = str(self.graph.value(execution_uri, EXEC.governedBy, default=""))
        approval_count = len(list(self.graph.objects(URIRef(action), EXEC.requiresApproval))) if action else 0
        outcome = str(self.graph.value(execution_uri, EXEC.producedOutcome, default=""))
        text = (
            "Goal → Workflow → Plan → Policy → Approval → Action: "
            f"execution {execution_uri} ran action {action} under policy {policy}; "
            f"approvals linked={approval_count}; outcome={outcome}."
        )
        explanation = new_uri("explanation")
        self.graph.add((explanation, RDF.type, EXEC.ExecutionExplanation))
        self.graph.add((explanation, EXEC.explainsExecution, execution_uri))
        self.graph.add((explanation, EXEC.explanationText, Literal(text)))
        add_activity(self.graph, EXEC.ExecutionExplained, "Execution explained", used=[execution_uri], generated=explanation)
        return ExecutionExplanation(str(explanation), str(execution_uri), text)
