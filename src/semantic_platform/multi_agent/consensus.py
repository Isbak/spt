"""Configurable consensus rules for collaborative decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS, XSD

from semantic_platform.multi_agent.common import AGGOV, MA, add_prov_activity, bind, now_literal, text


class ConsensusMethod(StrEnum):
    UNANIMOUS = "Unanimous"
    MAJORITY = "Majority"
    WEIGHTED = "Weighted"
    GOVERNANCE_APPROVED = "GovernanceApproved"


@dataclass(frozen=True)
class ConsensusRecord:
    uri: str
    method: str
    decision: str
    approved: bool
    agreement_rate: float


class ConsensusService:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def decide(self, decision: str, votes: dict[str, bool], *, method: ConsensusMethod = ConsensusMethod.MAJORITY, weights: dict[str, float] | None = None, actor: str = "orchestrator-agent") -> ConsensusRecord:
        consensus = URIRef(MA[f"consensus-{len(list(self.graph.subjects(RDF.type, MA.AgentConsensus))) + 1}"])
        weights = weights or {agent: 1.0 for agent in votes}
        approved = self._approved(votes, method, weights)
        rate = self._agreement_rate(votes, weights)
        self.graph.add((consensus, RDF.type, MA.AgentConsensus))
        self.graph.add((consensus, RDFS.label, Literal("Agent consensus")))
        self.graph.add((consensus, MA.consensusMethod, Literal(method.value)))
        self.graph.add((consensus, MA.decisionText, Literal(decision)))
        self.graph.add((consensus, MA.agreementRate, Literal(rate, datatype=XSD.decimal)))
        self.graph.add((consensus, MA.consensusApproved, Literal(approved, datatype=XSD.boolean)))
        self.graph.add((consensus, AGGOV.approvalStatus, Literal("Approved" if approved else "EscalationRequired")))
        self.graph.add((consensus, PROV.generatedAtTime, now_literal()))
        for agent, agrees in votes.items():
            pred = MA.agreedWith if agrees else MA.disagreedWith
            self.graph.add((consensus, pred, URIRef(agent) if agent.startswith("http") else URIRef(MA[agent])))
        add_prov_activity(self.graph, MA.ConsensusActivity, "Evaluate agent consensus", actor, generated=consensus)
        return self._record(consensus)

    def consensuses(self) -> list[ConsensusRecord]:
        return [self._record(c) for c in self.graph.subjects(RDF.type, MA.AgentConsensus)]

    def _approved(self, votes: dict[str, bool], method: ConsensusMethod, weights: dict[str, float]) -> bool:
        if not votes:
            return False
        if method == ConsensusMethod.UNANIMOUS:
            return all(votes.values())
        if method == ConsensusMethod.GOVERNANCE_APPROVED:
            return all(votes.values()) and len(votes) >= 2
        if method == ConsensusMethod.WEIGHTED:
            total = sum(weights.values()) or 1.0
            yes = sum(weights.get(a, 1.0) for a, vote in votes.items() if vote)
            return yes / total >= 0.6
        return sum(1 for vote in votes.values() if vote) > len(votes) / 2

    def _agreement_rate(self, votes: dict[str, bool], weights: dict[str, float]) -> float:
        total = sum(weights.values()) or 1.0
        yes = sum(weights.get(agent, 1.0) for agent, vote in votes.items() if vote)
        return round(yes / total, 4)

    def _record(self, consensus: URIRef) -> ConsensusRecord:
        return ConsensusRecord(str(consensus), text(self.graph, consensus, MA.consensusMethod), text(self.graph, consensus, MA.decisionText), text(self.graph, consensus, MA.consensusApproved) == "true", float(self.graph.value(consensus, MA.agreementRate, default=0) or 0))
