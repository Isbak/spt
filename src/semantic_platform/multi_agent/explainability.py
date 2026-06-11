"""Explainable collaboration decision traces."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef

from semantic_platform.multi_agent.common import MA, bind, text


@dataclass(frozen=True)
class CollaborationExplanation:
    decision: str
    text: str
    agents: tuple[str, ...]
    alternatives: tuple[str, ...]
    consensus_method: str


class CollaborationExplainer:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def explain(self, consensus: str) -> CollaborationExplanation:
        consensus_uri = URIRef(consensus)
        decision = text(self.graph, consensus_uri, MA.decisionText)
        agents = tuple(str(a) for a in self.graph.objects(consensus_uri, MA.agreedWith)) + tuple(str(a) for a in self.graph.objects(consensus_uri, MA.disagreedWith))
        alternatives = tuple(str(r) for negotiation in self.graph.subjects(MA.proposedDecision, None) for r in self.graph.objects(negotiation, MA.evaluatedRecommendation))
        method = text(self.graph, consensus_uri, MA.consensusMethod)
        explanation = (
            f"Goal → Agents Involved ({len(agents)}) → Alternatives Considered ({len(alternatives)}) "
            f"→ Consensus Method ({method}) → Decision ({decision})"
        )
        return CollaborationExplanation(decision, explanation, agents, alternatives, method)
