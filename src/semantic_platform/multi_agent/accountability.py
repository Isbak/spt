"""Accountability records for attributable agent actions."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF

from semantic_platform.multi_agent.common import MA, add_prov_activity, bind, local_id, now_literal, text


@dataclass(frozen=True)
class AccountabilityRecord:
    uri: str
    actor: str
    team: str
    role: str
    task: str
    outcome: str


class AccountabilityLog:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def record(self, actor: str, team: str, role: str, task: str, outcome: str) -> AccountabilityRecord:
        record = URIRef(MA[f"accountability-{local_id(actor)}-{local_id(task)}"])
        actor_uri = URIRef(actor) if actor.startswith("http") else URIRef(MA[actor])
        self.graph.add((record, RDF.type, MA.AgentAccountabilityRecord))
        self.graph.add((record, PROV.wasAttributedTo, actor_uri))
        self.graph.add((record, MA.team, URIRef(team) if team.startswith("http") else URIRef(MA[team])))
        self.graph.add((record, MA.role, URIRef(role) if role.startswith("http") else URIRef(MA[role])))
        self.graph.add((record, MA.accountableTask, URIRef(task) if task.startswith("http") else URIRef(MA[task])))
        self.graph.add((record, MA.outcome, Literal(outcome)))
        self.graph.add((record, PROV.generatedAtTime, now_literal()))
        add_prov_activity(self.graph, MA.AccountabilityActivity, "Record agent accountability", actor, generated=record)
        return self._record(record)

    def records(self) -> list[AccountabilityRecord]:
        return [self._record(record) for record in self.graph.subjects(RDF.type, MA.AgentAccountabilityRecord)]

    def _record(self, record: URIRef) -> AccountabilityRecord:
        return AccountabilityRecord(
            str(record), str(self.graph.value(record, PROV.wasAttributedTo, default="")), str(self.graph.value(record, MA.team, default="")), str(self.graph.value(record, MA.role, default="")), str(self.graph.value(record, MA.accountableTask, default="")), text(self.graph, record, MA.outcome),
        )
