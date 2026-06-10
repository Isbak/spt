"""Governed tool framework for agents."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from rdflib import Graph

from semantic_platform.agents.observations import AgentObservationLog, ObservationType
from semantic_platform.agents.registry import AgentRecord
from semantic_platform.agents.safety import require_safe_action
from semantic_platform.analytics import analytics_summary
from semantic_platform.governance import graph_assets
from semantic_platform.provenance import provenance_chain
from semantic_platform.query import execute_query, result_rows
from semantic_platform.search import search_graph


@dataclass(frozen=True)
class AgentTool:
    """A governed callable available to approved agents."""

    tool_id: str
    label: str
    scope: str
    handler: Callable[..., Any]


class AgentToolRegistry:
    """Register and execute governed agent tools."""

    def __init__(self, graph: Graph | None = None, observations: AgentObservationLog | None = None) -> None:
        self.graph = graph
        self.observations = observations or AgentObservationLog()
        self._tools: dict[str, AgentTool] = {}
        self.register_defaults()

    def register(self, tool: AgentTool) -> None:
        """Register a governed tool."""
        self._tools[tool.tool_id] = tool

    def list_tools(self) -> list[AgentTool]:
        """Return registered tools."""
        return sorted(self._tools.values(), key=lambda tool: tool.tool_id)

    def execute(self, agent: AgentRecord, tool_id: str, **kwargs: Any) -> Any:
        """Execute a tool after policy, graph, and tool validation."""
        tool = self._tools[tool_id]
        require_safe_action(agent=agent, graph_scope=tool.scope, tool_id=tool_id)
        self.observations.record(agent, ObservationType.TOOL_USAGE, f"Used {tool_id}", scope=tool.scope)
        return tool.handler(**kwargs)

    def register_defaults(self) -> None:
        """Register built-in semantic platform tools."""
        self.register(AgentTool("graph-query", "Graph Query Tool", "reasoning", self.graph_query))
        self.register(AgentTool("semantic-search", "Search Tool", "reference", self.semantic_search))
        self.register(AgentTool("provenance-lookup", "Provenance Tool", "provenance", self.provenance_lookup))
        self.register(AgentTool("governance-lookup", "Governance Tool", "governance", self.governance_lookup))
        self.register(AgentTool("graph-analytics", "Analytics Tool", "reasoning", self.graph_analytics))

    def graph_query(self, query_text: str) -> list[dict[str, Any]]:
        """Run SPARQL against the configured local graph."""
        return result_rows(execute_query(query_text, self.graph)) if self.graph is not None else result_rows(execute_query(query_text))

    def semantic_search(self, query: str) -> list[dict[str, str]]:
        """Run semantic search."""
        return [result.__dict__ for result in search_graph(query, graph=self.graph)]

    def provenance_lookup(self, resource: str) -> list[dict[str, str]]:
        """Return provenance chain rows for a resource."""
        return provenance_chain(resource, graph=self.graph)

    def governance_lookup(self) -> list[dict[str, str | None]]:
        """Return governed graph asset ownership metadata."""
        return [asset.__dict__ for asset in graph_assets(graph=self.graph)]

    def graph_analytics(self) -> dict[str, int | float]:
        """Return graph analytics metrics."""
        return analytics_summary(graph=self.graph).__dict__
