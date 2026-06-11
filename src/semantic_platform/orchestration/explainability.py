"""Explainable orchestration rationale stored as RDF."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from semantic_platform.orchestration.common import ORCH, add_activity, bind, new_uri


@dataclass(frozen=True)
class OrchestrationExplanation:
    """Explanation for a coordination or planning recommendation."""

    uri: str
    recommendation: str
    text: str


class ExplanationService:
    """Record recommendation rationale including goals, inputs, dependencies, policies, and approvals."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def explain(self, recommendation: str | URIRef, *, goal: str, inputs: list[str], dependencies: list[str], policies: list[str], approvals: list[str]) -> OrchestrationExplanation:
        recommendation_uri = URIRef(str(recommendation))
        explanation = new_uri("orchestration-explanation")
        text = (
            f"Goal: {goal}. Inputs: {', '.join(inputs) or 'none'}. "
            f"Dependencies: {', '.join(dependencies) or 'none'}. "
            f"Policies applied: {', '.join(policies) or 'none'}. "
            f"Approvals required: {', '.join(approvals) or 'none'}."
        )
        self.graph.add((explanation, RDF.type, ORCH.OrchestrationExplanation))
        self.graph.add((explanation, ORCH.explainsRecommendation, recommendation_uri))
        self.graph.add((explanation, ORCH.explanationText, Literal(text)))
        self.graph.add((recommendation_uri, ORCH.hasExplanation, explanation))
        add_activity(self.graph, ORCH.ExplanationRecorded, "Recorded orchestration explanation", used=[recommendation_uri], generated=explanation)
        return OrchestrationExplanation(str(explanation), str(recommendation_uri), text)
