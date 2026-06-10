"""Agent observability and metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.agents.registry import AGENT, AgentRecord


class ObservationType(StrEnum):
    """Observable agent event types."""

    REQUEST = "request"
    ACTION = "action"
    FAILURE = "failure"
    WARNING = "warning"
    GRAPH_ACCESS = "graph_access"
    TOOL_USAGE = "tool_usage"


@dataclass(frozen=True)
class AgentObservation:
    """One observable event emitted by an agent interaction."""

    observation_id: str
    agent_id: str
    event_type: ObservationType
    message: str
    timestamp: datetime
    scope: str | None = None


class AgentObservationLog:
    """In-memory observation log with RDF representation and metrics."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph or Graph()
        self._events: list[AgentObservation] = []

    def record(
        self,
        agent: AgentRecord,
        event_type: ObservationType,
        message: str,
        *,
        scope: str | None = None,
    ) -> AgentObservation:
        """Record an agent request, action, warning, failure, graph access, or tool usage."""
        timestamp = datetime.now(UTC)
        observation_uri = URIRef(AGENT[f"observation-{uuid4()}"])
        self.graph.add((observation_uri, RDF.type, AGENT.AgentObservation))
        self.graph.add((observation_uri, AGENT.observationType, Literal(event_type.value)))
        self.graph.add((observation_uri, AGENT.observationMessage, Literal(message)))
        self.graph.add((observation_uri, AGENT.observedAt, Literal(timestamp.isoformat(), datatype=XSD.dateTime)))
        self.graph.add((URIRef(agent.uri), AGENT.hasObservation, observation_uri))
        if scope:
            self.graph.add((observation_uri, AGENT.graphScope, Literal(scope)))
        event = AgentObservation(str(observation_uri), agent.agent_id, event_type, message, timestamp, scope)
        self._events.append(event)
        return event

    def observations(self, agent_id: str | None = None) -> list[AgentObservation]:
        """Return recorded observations, optionally filtered by agent id."""
        return [event for event in self._events if agent_id is None or event.agent_id == agent_id]

    def metrics(self) -> dict[str, int]:
        """Expose aggregate observability metrics."""
        counts = Counter(event.event_type.value for event in self._events)
        return {
            "requests": counts[ObservationType.REQUEST.value],
            "actions": counts[ObservationType.ACTION.value],
            "failures": counts[ObservationType.FAILURE.value],
            "warnings": counts[ObservationType.WARNING.value],
            "graph_accesses": counts[ObservationType.GRAPH_ACCESS.value],
            "tool_usages": counts[ObservationType.TOOL_USAGE.value],
        }
