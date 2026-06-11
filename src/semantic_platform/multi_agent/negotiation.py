"""Negotiation framework for comparing agent recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS, XSD

from semantic_platform.multi_agent.common import MA, add_prov_activity, bind, local_id, now_literal, slug, text


@dataclass(frozen=True)
class RecommendationRecord:
    uri: str
    actor: str
    option: str
    rationale: str
    score: float


@dataclass(frozen=True)
class NegotiationRecord:
    uri: str
    recommendations: tuple[str, ...]
    selected: str
    compromise: str


class NegotiationService:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def recommend(self, actor: str, option: str, rationale: str, score: float) -> RecommendationRecord:
        rec = URIRef(MA[f"recommendation-{slug(local_id(actor))}-{slug(local_id(option))}"])
        self.graph.add((rec, RDF.type, MA.AgentRecommendation))
        self.graph.add((rec, PROV.wasAttributedTo, URIRef(actor) if actor.startswith("http") else URIRef(MA[actor])))
        self.graph.add((rec, MA.recommendedOption, Literal(option)))
        self.graph.add((rec, MA.rationale, Literal(rationale)))
        self.graph.add((rec, MA.optionScore, Literal(score, datatype=XSD.decimal)))
        self.graph.add((rec, PROV.generatedAtTime, now_literal()))
        add_prov_activity(self.graph, MA.RecommendationActivity, "Create agent recommendation", actor, generated=rec)
        return self._recommendation(rec)

    def negotiate(self, recommendations: list[str], *, actor: str = "orchestrator-agent") -> NegotiationRecord:
        negotiation = URIRef(MA[f"negotiation-{len(list(self.graph.subjects(RDF.type, MA.AgentNegotiation))) + 1}"])
        ranked = sorted((URIRef(r), float(self.graph.value(URIRef(r), MA.optionScore, default=0) or 0)) for r in recommendations)
        ranked = sorted(ranked, key=lambda item: item[1], reverse=True)
        selected = ranked[0][0] if ranked else URIRef(MA["no-recommendation"])
        compromise = self._compromise(ranked)
        self.graph.add((negotiation, RDF.type, MA.AgentNegotiation))
        self.graph.add((negotiation, RDFS.label, Literal("Recommendation negotiation")))
        self.graph.add((negotiation, MA.proposedDecision, selected))
        self.graph.add((negotiation, MA.compromiseOption, Literal(compromise)))
        self.graph.add((negotiation, PROV.generatedAtTime, now_literal()))
        for rec, _score in ranked:
            self.graph.add((negotiation, MA.evaluatedRecommendation, rec))
        add_prov_activity(self.graph, MA.NegotiationActivity, "Negotiate recommendations", actor, used=[r for r, _s in ranked], generated=negotiation)
        return self._negotiation(negotiation)

    def negotiations(self) -> list[NegotiationRecord]:
        return [self._negotiation(n) for n in self.graph.subjects(RDF.type, MA.AgentNegotiation)]

    def _compromise(self, ranked: list[tuple[URIRef, float]]) -> str:
        if len(ranked) <= 1:
            return text(self.graph, ranked[0][0], MA.recommendedOption) if ranked else "No option"
        top = [text(self.graph, rec, MA.recommendedOption) for rec, _score in ranked[:2]]
        return "Compromise: " + " + ".join(top)

    def _recommendation(self, rec: URIRef) -> RecommendationRecord:
        return RecommendationRecord(str(rec), str(self.graph.value(rec, PROV.wasAttributedTo, default="")), text(self.graph, rec, MA.recommendedOption), text(self.graph, rec, MA.rationale), float(self.graph.value(rec, MA.optionScore, default=0) or 0))

    def _negotiation(self, negotiation: URIRef) -> NegotiationRecord:
        return NegotiationRecord(str(negotiation), tuple(str(r) for r in self.graph.objects(negotiation, MA.evaluatedRecommendation)), str(self.graph.value(negotiation, MA.proposedDecision, default="")), text(self.graph, negotiation, MA.compromiseOption))
