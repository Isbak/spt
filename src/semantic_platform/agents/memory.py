"""Agent memory stores represented as RDF resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from semantic_platform.agents.registry import AGENT, AgentRecord

PROV = Namespace("http://www.w3.org/ns/prov#")


class MemoryType(StrEnum):
    """Supported agent memory types."""

    WORKING = "WorkingMemory"
    SESSION = "SessionMemory"
    SEMANTIC = "SemanticMemory"
    OBSERVATION = "ObservationMemory"


@dataclass(frozen=True)
class MemoryEntry:
    """A serializable agent memory record."""

    memory_id: str
    agent_id: str
    memory_type: MemoryType
    content: str
    created_at: datetime
    session_id: str | None = None


class AgentMemoryStore:
    """In-memory RDF-backed memory store suitable for API and tests.

    Persistence can be added later by serializing ``graph`` to a sandbox or integration graph.
    """

    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph or Graph()

    def remember(
        self,
        agent: AgentRecord,
        memory_type: MemoryType,
        content: str,
        *,
        session_id: str | None = None,
    ) -> MemoryEntry:
        """Store a memory entry as RDF."""
        created_at = datetime.now(UTC)
        memory_uri = URIRef(AGENT[f"memory-{uuid4()}"])
        agent_uri = URIRef(agent.uri)
        self.graph.add((memory_uri, RDF.type, AGENT.AgentMemory))
        self.graph.add((memory_uri, RDF.type, AGENT[memory_type.value]))
        self.graph.add((memory_uri, RDFS.label, Literal(f"{memory_type.value} for {agent.agent_id}")))
        self.graph.add((memory_uri, AGENT.memoryContent, Literal(content)))
        self.graph.add((memory_uri, AGENT.memoryType, Literal(memory_type.value)))
        self.graph.add((memory_uri, PROV.generatedAtTime, Literal(created_at.isoformat(), datatype=XSD.dateTime)))
        self.graph.add((agent_uri, AGENT.hasMemory, memory_uri))
        if session_id:
            self.graph.add((memory_uri, AGENT.sessionId, Literal(session_id)))
        return MemoryEntry(str(memory_uri), agent.agent_id, memory_type, content, created_at, session_id)

    def recall(self, agent: AgentRecord, memory_type: MemoryType | None = None) -> list[MemoryEntry]:
        """Retrieve memory entries for an agent."""
        entries: list[MemoryEntry] = []
        agent_uri = URIRef(agent.uri)
        for memory in self.graph.objects(agent_uri, AGENT.hasMemory):
            stored_type = str(self.graph.value(memory, AGENT.memoryType) or MemoryType.WORKING.value)
            if memory_type and stored_type != memory_type.value:
                continue
            content = str(self.graph.value(memory, AGENT.memoryContent) or "")
            session = self.graph.value(memory, AGENT.sessionId)
            entries.append(
                MemoryEntry(str(memory), agent.agent_id, MemoryType(stored_type), content, datetime.now(UTC), str(session) if session else None)
            )
        return entries
