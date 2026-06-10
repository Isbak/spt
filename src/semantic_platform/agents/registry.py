"""Agent registry backed by governed RDF metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, OWL

from semantic_platform.agents.permissions import PermissionSet
from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

AGENT = Namespace("https://example.org/semantic-platform/agents#")
AGGOV = Namespace("https://example.org/semantic-platform/agent-governance#")


class AgentStatus(StrEnum):
    """Governed lifecycle statuses for registered agents."""

    DRAFT = "Draft"
    TESTING = "Testing"
    APPROVED = "Approved"
    DEPRECATED = "Deprecated"
    RETIRED = "Retired"


@dataclass(frozen=True)
class AgentRecord:
    """One managed agent entry from the agent registry."""

    agent_id: str
    uri: str
    label: str
    owner: str
    steward: str
    version: str
    status: AgentStatus
    capabilities: tuple[str, ...]
    allowed_graphs: tuple[str, ...]
    allowed_tools: tuple[str, ...]

    @property
    def permissions(self) -> PermissionSet:
        """Return executable permission checks for this agent."""
        writable = tuple(scope for scope in self.allowed_graphs if scope in {"sandbox", "integration"})
        return PermissionSet(
            read_graphs=frozenset(self.allowed_graphs),
            write_graphs=frozenset(writable),
            tools=frozenset(self.allowed_tools),
        )


def _text(graph: Graph, subject: URIRef, predicate: URIRef, default: str = "") -> str:
    value = graph.value(subject, predicate)
    return str(value) if value is not None else default


def _local_id(uri: URIRef) -> str:
    text = str(uri)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


class AgentRegistry:
    """Read-only registry for governed agent metadata."""

    def __init__(self, graph: Graph | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.graph = graph or load_graph(
            [self.settings.vocabularies_dir, self.settings.data_dir], settings=self.settings
        )

    def list_agents(self) -> list[AgentRecord]:
        """Return all registered, non-anonymous agents."""
        agents = sorted(set(self.graph.subjects(RDF.type, AGENT.Agent)), key=str)
        return [self._record(URIRef(agent)) for agent in agents]

    def get(self, agent_id: str) -> AgentRecord | None:
        """Return one agent by local id or URI."""
        for record in self.list_agents():
            if agent_id in {record.agent_id, record.uri}:
                return record
        return None

    def require(self, agent_id: str) -> AgentRecord:
        """Return one agent or raise ``KeyError``."""
        record = self.get(agent_id)
        if record is None:
            raise KeyError(f"Agent is not registered: {agent_id}")
        return record

    def validate(self) -> list[str]:
        """Return registry governance validation errors."""
        errors: list[str] = []
        for record in self.list_agents():
            if not record.owner:
                errors.append(f"{record.agent_id} has no owner")
            if not record.steward:
                errors.append(f"{record.agent_id} has no steward")
            if not record.version:
                errors.append(f"{record.agent_id} has no version")
            if record.status not in set(AgentStatus):
                errors.append(f"{record.agent_id} has unsupported status {record.status}")
            if not record.allowed_graphs:
                errors.append(f"{record.agent_id} has no allowed graph access")
            if not record.allowed_tools:
                errors.append(f"{record.agent_id} has no allowed tools")
        if not self.list_agents():
            errors.append("agent registry contains no managed agents")
        return errors

    def _record(self, uri: URIRef) -> AgentRecord:
        status_text = _text(self.graph, uri, AGGOV.approvalStatus, AgentStatus.DRAFT.value)
        capabilities = tuple(
            sorted(_text(self.graph, URIRef(cap), RDFS.label, _local_id(URIRef(cap))) for cap in self.graph.objects(uri, AGENT.hasCapability))
        )
        allowed_graphs = tuple(sorted(str(scope) for scope in self.graph.objects(uri, AGGOV.allowedGraphAccess)))
        allowed_tools = tuple(sorted(_local_id(URIRef(tool)) for tool in self.graph.objects(uri, AGGOV.allowedTool)))
        return AgentRecord(
            agent_id=_local_id(uri),
            uri=str(uri),
            label=_text(self.graph, uri, RDFS.label, _local_id(uri)),
            owner=_text(self.graph, uri, AGGOV.owner),
            steward=_text(self.graph, uri, AGGOV.steward),
            version=_text(self.graph, uri, OWL.versionInfo) or _text(self.graph, uri, DCTERMS.hasVersion),
            status=AgentStatus(status_text),
            capabilities=capabilities,
            allowed_graphs=allowed_graphs,
            allowed_tools=allowed_tools,
        )
