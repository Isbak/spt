"""Coordination recommendations across humans, agents, and workflows."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from semantic_platform.orchestration.common import ORCH, add_activity, bind, new_uri


@dataclass(frozen=True)
class CoordinationRecommendation:
    """Non-executing assignment recommendation."""

    uri: str
    task: str
    participant: str
    participant_type: str
    rationale: str


class CoordinationService:
    """Recommend task assignments while preserving human control."""

    PARTICIPANTS = {"Human", "Agent", "Workflow"}

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def recommend_assignment(self, task: str | URIRef, participant: str, participant_type: str, rationale: str) -> CoordinationRecommendation:
        if participant_type not in self.PARTICIPANTS:
            raise ValueError(f"unsupported participant type: {participant_type}")
        task_uri = URIRef(str(task))
        recommendation = new_uri("coordination")
        self.graph.add((recommendation, RDF.type, ORCH.CoordinationRecommendation))
        self.graph.add((recommendation, ORCH.assignedTo, Literal(participant)))
        self.graph.add((recommendation, ORCH.participantType, Literal(participant_type)))
        self.graph.add((recommendation, ORCH.rationale, Literal(rationale)))
        self.graph.add((task_uri, ORCH.hasRecommendation, recommendation))
        add_activity(self.graph, ORCH.CoordinationRecommended, "Created coordination recommendation", used=[task_uri], generated=recommendation)
        return CoordinationRecommendation(str(recommendation), str(task_uri), participant, participant_type, rationale)
