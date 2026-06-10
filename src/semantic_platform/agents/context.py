"""Semantic context retrieval for governed agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from semantic_platform.agents.registry import AgentRecord
from semantic_platform.agents.safety import require_safe_action
from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph


_SCOPE_DIRS = {
    "ontology": "ontology_dir",
    "reference": "vocabularies_dir",
    "governance": "vocabularies_dir",
    "provenance": "data_dir",
    "reasoning": "data_dir",
}


@dataclass(frozen=True)
class AgentContext:
    """Graph-backed context supplied to an agent."""

    agent_id: str
    scope: str
    triples: int
    graph: Graph


def _paths_for_scope(settings: Settings, scope: str) -> list[Path]:
    attr = _SCOPE_DIRS.get(scope)
    return [getattr(settings, attr)] if attr else []


class AgentContextProvider:
    """Retrieve governed semantic, ontology, governance, provenance, and reasoning context."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def retrieve(self, agent: AgentRecord, scope: str) -> AgentContext:
        """Retrieve RDF context for a permitted graph scope."""
        require_safe_action(agent=agent, graph_scope=scope)
        graph = load_graph(_paths_for_scope(self.settings, scope), settings=self.settings)
        return AgentContext(agent_id=agent.agent_id, scope=scope, triples=len(graph), graph=graph)

    def semantic_context(self, agent: AgentRecord) -> AgentContext:
        """Retrieve reference semantic vocabulary context."""
        return self.retrieve(agent, "reference")

    def ontology_context(self, agent: AgentRecord) -> AgentContext:
        """Retrieve ontology context."""
        return self.retrieve(agent, "ontology")

    def governance_context(self, agent: AgentRecord) -> AgentContext:
        """Retrieve governance context."""
        return self.retrieve(agent, "governance")

    def provenance_context(self, agent: AgentRecord) -> AgentContext:
        """Retrieve provenance context."""
        return self.retrieve(agent, "provenance")

    def reasoning_context(self, agent: AgentRecord) -> AgentContext:
        """Retrieve reasoning context."""
        return self.retrieve(agent, "reasoning")
