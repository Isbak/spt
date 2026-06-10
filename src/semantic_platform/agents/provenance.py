"""PROV-O extensions for agent executions, observations, decisions, and outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.agents.registry import AGENT, AgentRecord

PROV = Namespace("http://www.w3.org/ns/prov#")


@dataclass(frozen=True)
class AgentProvenanceChain:
    """Agent -> execution -> observation -> decision -> output provenance chain."""

    agent: str
    execution: str
    observation: str
    decision: str
    output: str
    timestamp: datetime


class AgentProvenanceRecorder:
    """Create RDF provenance records for every governed agent action."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph or Graph()

    def record_execution(
        self,
        agent: AgentRecord,
        *,
        request_user: str,
        tools_used: list[str] | None = None,
        graphs_accessed: list[str] | None = None,
        output_text: str = "",
    ) -> AgentProvenanceChain:
        """Create a complete execution provenance chain."""
        timestamp = datetime.now(UTC)
        agent_uri = URIRef(agent.uri)
        execution = URIRef(AGENT[f"execution-{uuid4()}"])
        observation = URIRef(AGENT[f"observation-{uuid4()}"])
        decision = URIRef(AGENT[f"decision-{uuid4()}"])
        output = URIRef(AGENT[f"output-{uuid4()}"])

        self.graph.add((agent_uri, RDF.type, AGENT.Agent))
        self.graph.add((execution, RDF.type, AGENT.AgentExecution))
        self.graph.add((execution, RDF.type, PROV.Activity))
        self.graph.add((execution, PROV.wasAssociatedWith, agent_uri))
        self.graph.add((execution, PROV.startedAtTime, Literal(timestamp.isoformat(), datatype=XSD.dateTime)))
        self.graph.add((execution, AGENT.agentVersion, Literal(agent.version)))
        self.graph.add((execution, AGENT.initiatingUser, Literal(request_user)))
        self.graph.add((agent_uri, AGENT.performedExecution, execution))

        self.graph.add((observation, RDF.type, AGENT.AgentObservation))
        self.graph.add((observation, PROV.wasGeneratedBy, execution))
        self.graph.add((execution, AGENT.hasObservation, observation))
        self.graph.add((decision, RDF.type, AGENT.AgentDecision))
        self.graph.add((decision, PROV.wasDerivedFrom, observation))
        self.graph.add((agent_uri, AGENT.proposedDecision, decision))
        self.graph.add((output, RDF.type, AGENT.AgentOutput))
        self.graph.add((output, PROV.wasDerivedFrom, decision))
        self.graph.add((agent_uri, AGENT.generatedOutput, output))
        if output_text:
            self.graph.add((output, AGENT.outputText, Literal(output_text)))
        for tool in tools_used or []:
            self.graph.add((execution, AGENT.usedTool, URIRef(AGENT[tool])))
        for graph_scope in graphs_accessed or []:
            self.graph.add((execution, AGENT.accessedGraph, Literal(graph_scope)))
        return AgentProvenanceChain(str(agent_uri), str(execution), str(observation), str(decision), str(output), timestamp)

    def chains(self, agent: AgentRecord) -> list[AgentProvenanceChain]:
        """Return recorded chains for an agent."""
        chains: list[AgentProvenanceChain] = []
        agent_uri = URIRef(agent.uri)
        for execution in self.graph.objects(agent_uri, AGENT.performedExecution):
            observation = self.graph.value(execution, AGENT.hasObservation)
            decision = self.graph.value(agent_uri, AGENT.proposedDecision)
            output = self.graph.value(agent_uri, AGENT.generatedOutput)
            chains.append(
                AgentProvenanceChain(
                    str(agent_uri), str(execution), str(observation), str(decision), str(output), datetime.now(UTC)
                )
            )
        return chains
