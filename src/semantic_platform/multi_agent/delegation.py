"""Governed agent delegation service."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS

from semantic_platform.multi_agent.common import AGGOV, MA, add_prov_activity, bind, local_id, now_literal, text


@dataclass(frozen=True)
class DelegationRecord:
    uri: str
    task: str
    delegating_agent: str
    receiving_agent: str
    reason: str
    timestamp: str
    governed: bool


class DelegationService:
    """Convert goals into tasks assigned to specialist agents."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def create_task(self, goal: str, label: str) -> str:
        task = URIRef(MA[f"task-{label.lower().replace(' ', '-')}"])
        goal_uri = URIRef(goal) if goal.startswith("http") else URIRef(MA[goal])
        self.graph.add((task, RDF.type, MA.AgentTask))
        self.graph.add((task, RDFS.label, Literal(label)))
        self.graph.add((task, PROV.wasDerivedFrom, goal_uri))
        return str(task)

    def delegate(self, task: str, delegating_agent: str, receiving_agent: str, reason: str, *, team: str = "") -> DelegationRecord:
        delegation = URIRef(MA[f"delegation-{local_id(task)}-{local_id(receiving_agent)}"])
        task_uri = URIRef(task) if task.startswith("http") else URIRef(MA[task])
        delegator = URIRef(delegating_agent) if delegating_agent.startswith("http") else URIRef(MA[delegating_agent])
        receiver = URIRef(receiving_agent) if receiving_agent.startswith("http") else URIRef(MA[receiving_agent])
        self.graph.add((delegation, RDF.type, MA.AgentDelegation))
        self.graph.add((delegation, MA.assignedTask, task_uri))
        self.graph.add((delegation, MA.delegatingAgent, delegator))
        self.graph.add((delegation, MA.delegatesTo, receiver))
        self.graph.add((delegation, MA.delegationReason, Literal(reason)))
        self.graph.add((delegation, PROV.generatedAtTime, now_literal()))
        self.graph.add((delegation, AGGOV.approvalStatus, Literal("Approved")))
        if team:
            self.graph.add((delegation, MA.team, URIRef(team) if team.startswith("http") else URIRef(MA[team])))
        self.graph.add((receiver, MA.assignedTask, task_uri))
        add_prov_activity(self.graph, MA.DelegationActivity, "Delegate governed agent task", delegating_agent, used=[task_uri], generated=delegation)
        return self._record(delegation)

    def delegations(self) -> list[DelegationRecord]:
        return [self._record(d) for d in self.graph.subjects(RDF.type, MA.AgentDelegation)]

    def _record(self, delegation: URIRef) -> DelegationRecord:
        return DelegationRecord(
            str(delegation), str(self.graph.value(delegation, MA.assignedTask, default="")), str(self.graph.value(delegation, MA.delegatingAgent, default="")), str(self.graph.value(delegation, MA.delegatesTo, default="")), text(self.graph, delegation, MA.delegationReason), text(self.graph, delegation, PROV.generatedAtTime), text(self.graph, delegation, AGGOV.approvalStatus) == "Approved"
        )
