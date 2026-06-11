"""Conflict detection, resolution, and escalation for agent collaboration."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS

from semantic_platform.multi_agent.common import MA, add_prov_activity, bind, local_id, now_literal, slug, text


@dataclass(frozen=True)
class ConflictRecord:
    uri: str
    conflict_type: str
    status: str
    resolution: str
    escalation: str


class ConflictResolutionService:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def detect(self, left: str, right: str, conflict_type: str, reason: str) -> ConflictRecord:
        conflict = URIRef(MA[f"conflict-{slug(local_id(left))}-{slug(local_id(right))}"])
        self.graph.add((conflict, RDF.type, MA.AgentConflict))
        self.graph.add((conflict, RDFS.label, Literal(reason)))
        self.graph.add((conflict, MA.conflictType, Literal(conflict_type)))
        self.graph.add((conflict, MA.conflictStatus, Literal("Detected")))
        self.graph.add((conflict, PROV.wasDerivedFrom, URIRef(left) if left.startswith("http") else URIRef(MA[left])))
        self.graph.add((conflict, PROV.wasDerivedFrom, URIRef(right) if right.startswith("http") else URIRef(MA[right])))
        self.graph.add((conflict, PROV.generatedAtTime, now_literal()))
        add_prov_activity(self.graph, MA.ConflictActivity, "Detect collaboration conflict", "observer-agent", generated=conflict)
        return self._record(conflict)

    def resolve(self, conflict: str, resolution: str, *, actor: str = "governance-agent") -> ConflictRecord:
        conflict_uri = URIRef(conflict)
        resolution_uri = URIRef(MA[f"resolution-{slug(local_id(conflict))}"])
        self.graph.add((resolution_uri, RDF.type, MA.AgentConflictResolution))
        self.graph.add((resolution_uri, MA.resolutionText, Literal(resolution)))
        self.graph.remove((conflict_uri, MA.conflictStatus, None))
        self.graph.add((conflict_uri, MA.conflictStatus, Literal("Resolved")))
        self.graph.add((conflict_uri, MA.hasResolution, resolution_uri))
        add_prov_activity(self.graph, MA.ConflictResolutionActivity, "Resolve collaboration conflict", actor, used=[conflict_uri], generated=resolution_uri)
        return self._record(conflict_uri)

    def escalate(self, conflict: str, target: str, reason: str, *, actor: str = "governance-agent") -> ConflictRecord:
        conflict_uri = URIRef(conflict)
        escalation = URIRef(MA[f"escalation-{slug(local_id(conflict))}"])
        self.graph.add((escalation, RDF.type, MA.AgentConflictEscalation))
        self.graph.add((escalation, MA.escalationReason, Literal(reason)))
        self.graph.remove((conflict_uri, MA.conflictStatus, None))
        self.graph.add((conflict_uri, MA.conflictStatus, Literal("Escalated")))
        self.graph.add((conflict_uri, MA.escalatedTo, URIRef(target) if target.startswith("http") else URIRef(MA[target])))
        self.graph.add((conflict_uri, MA.hasEscalation, escalation))
        add_prov_activity(self.graph, MA.ConflictEscalationActivity, "Escalate collaboration conflict", actor, used=[conflict_uri], generated=escalation)
        return self._record(conflict_uri)

    def conflicts(self) -> list[ConflictRecord]:
        return [self._record(c) for c in self.graph.subjects(RDF.type, MA.AgentConflict)]

    def _record(self, conflict: URIRef) -> ConflictRecord:
        resolution = self.graph.value(conflict, MA.hasResolution)
        escalation = self.graph.value(conflict, MA.hasEscalation)
        return ConflictRecord(str(conflict), text(self.graph, conflict, MA.conflictType), text(self.graph, conflict, MA.conflictStatus), text(self.graph, URIRef(resolution), MA.resolutionText) if resolution else "", text(self.graph, URIRef(escalation), MA.escalationReason) if escalation else "")
