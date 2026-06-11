"""Event framework for semantic orchestration notifications and triggers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from semantic_platform.orchestration.common import ORCH, add_activity, add_label, bind, new_uri


@dataclass(frozen=True)
class OrchestrationEvent:
    """Recorded orchestration event."""

    uri: str
    event_type: str
    source: str
    message: str
    timestamp: str


class EventLog:
    """Store event sources, triggers, notifications, and workflow events as RDF."""

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = bind(graph if graph is not None else Graph())

    def record_event(self, event_type: str, source: str, message: str, *, workflow: str | URIRef | None = None) -> OrchestrationEvent:
        event = new_uri("event")
        now = datetime.now(UTC).isoformat()
        self.graph.add((event, RDF.type, ORCH.Event))
        self.graph.add((event, ORCH.eventType, Literal(event_type)))
        self.graph.add((event, ORCH.eventSource, Literal(source)))
        self.graph.add((event, ORCH.eventMessage, Literal(message)))
        self.graph.add((event, ORCH.occurredAt, Literal(now, datatype=XSD.dateTime)))
        add_label(self.graph, event, event_type)
        if workflow is not None:
            self.graph.add((URIRef(str(workflow)), ORCH.triggeredBy, event))
        add_activity(self.graph, ORCH.EventRecorded, f"Recorded event {event_type}", generated=event)
        return OrchestrationEvent(str(event), event_type, source, message, now)

    def events(self, event_type: str | None = None) -> list[OrchestrationEvent]:
        rows = []
        for event in sorted(set(self.graph.subjects(RDF.type, ORCH.Event)), key=str):
            row_type = str(self.graph.value(event, ORCH.eventType, default=""))
            if event_type and row_type != event_type:
                continue
            rows.append(OrchestrationEvent(str(event), row_type, str(self.graph.value(event, ORCH.eventSource, default="")), str(self.graph.value(event, ORCH.eventMessage, default="")), str(self.graph.value(event, ORCH.occurredAt, default=""))))
        return rows
