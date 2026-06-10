"""PROV-O-compatible provenance services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

PROV = Namespace("http://www.w3.org/ns/prov#")
SPPROV = Namespace("https://example.org/semantic-platform/provenance#")


@dataclass(frozen=True)
class ProvenanceActivity:
    """A serializable provenance activity record."""

    activity: str
    label: str
    agent: str
    started_at: datetime
    ended_at: datetime | None = None
    entity: str | None = None
    derived_from: str | None = None


def _dt(value: datetime) -> Literal:
    return Literal(value.astimezone(UTC).isoformat().replace("+00:00", "Z"), datatype=XSD.dateTime)


def create_provenance_record(
    label: str,
    agent: str,
    entity: str | None = None,
    derived_from: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> ProvenanceActivity:
    """Create an in-memory provenance activity record."""
    now = started_at or datetime.now(UTC)
    return ProvenanceActivity(
        activity=str(SPPROV[f"activity-{uuid4()}"]),
        label=label,
        agent=agent,
        started_at=now,
        ended_at=ended_at,
        entity=entity,
        derived_from=derived_from,
    )


def load_activity(agent: str, entity: str, started_at: datetime | None = None) -> ProvenanceActivity:
    """Represent a graph or dataset load activity."""
    return create_provenance_record("Graph load activity", agent, entity, started_at=started_at)


def validation_activity(agent: str, entity: str, started_at: datetime | None = None) -> ProvenanceActivity:
    """Represent an RDF validation activity."""
    return create_provenance_record("RDF validation activity", agent, entity, started_at=started_at)


def serialize_provenance(activity: ProvenanceActivity) -> Graph:
    """Serialize a provenance activity as an RDFLib graph using PROV-O terms."""
    graph = Graph()
    activity_ref = URIRef(activity.activity)
    agent_ref = URIRef(activity.agent)
    graph.add((activity_ref, RDF.type, PROV.Activity))
    graph.add((activity_ref, RDFS.label, Literal(activity.label)))
    graph.add((activity_ref, PROV.startedAtTime, _dt(activity.started_at)))
    graph.add((activity_ref, PROV.wasAssociatedWith, agent_ref))
    graph.add((agent_ref, RDF.type, PROV.Agent))
    if activity.ended_at is not None:
        graph.add((activity_ref, PROV.endedAtTime, _dt(activity.ended_at)))
    if activity.entity is not None:
        entity_ref = URIRef(activity.entity)
        graph.add((entity_ref, RDF.type, PROV.Entity))
        graph.add((entity_ref, PROV.wasGeneratedBy, activity_ref))
        if activity.derived_from is not None:
            graph.add((entity_ref, PROV.wasDerivedFrom, URIRef(activity.derived_from)))
    return graph


def load_provenance_graph(settings: Settings | None = None, graph: Graph | None = None) -> Graph:
    """Load provenance-capable local RDF assets."""
    settings = settings or load_settings()
    return graph or load_graph([settings.vocabularies_dir, settings.data_dir, settings.graphs_dir], settings)


def provenance_chain(resource: str, graph: Graph | None = None, settings: Settings | None = None) -> list[dict[str, str]]:
    """Query direct provenance activities for a graph or dataset resource."""
    graph = load_provenance_graph(settings=settings, graph=graph)
    resource_ref = URIRef(resource)
    rows: list[dict[str, str]] = []
    for activity in graph.objects(resource_ref, PROV.wasGeneratedBy):
        row = {"entity": str(resource_ref), "activity": str(activity)}
        label = graph.value(activity, RDFS.label)
        agent = graph.value(activity, PROV.wasAssociatedWith)
        started = graph.value(activity, PROV.startedAtTime)
        if label is not None:
            row["label"] = str(label)
        if agent is not None:
            row["agent"] = str(agent)
        if started is not None:
            row["started_at"] = str(started)
        rows.append(row)
    return rows
