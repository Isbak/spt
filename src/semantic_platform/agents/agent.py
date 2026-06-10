"""Generic non-domain-specific agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from semantic_platform.agents.context import AgentContextProvider
from semantic_platform.agents.memory import AgentMemoryStore, MemoryType
from semantic_platform.agents.observations import AgentObservationLog, ObservationType
from semantic_platform.agents.provenance import AgentProvenanceRecorder
from semantic_platform.agents.registry import AgentRegistry
from semantic_platform.agents.tools import AgentToolRegistry


@dataclass(frozen=True)
class AgentResponse:
    """Explainable response from a governed agent interaction."""

    agent_id: str
    output: str
    context_scope: str
    triples_seen: int
    provenance_execution: str


class AgentRuntime:
    """Generic runtime that lets approved agents inspect governed platform context.

    The runtime does not perform autonomous orchestration or workflow execution.
    """

    def __init__(
        self,
        *,
        registry: AgentRegistry | None = None,
        context_provider: AgentContextProvider | None = None,
        memory: AgentMemoryStore | None = None,
        observations: AgentObservationLog | None = None,
        provenance: AgentProvenanceRecorder | None = None,
        tools: AgentToolRegistry | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.context_provider = context_provider or AgentContextProvider()
        self.memory = memory or AgentMemoryStore()
        self.observations = observations or AgentObservationLog()
        self.provenance = provenance or AgentProvenanceRecorder()
        self.tools = tools or AgentToolRegistry(observations=self.observations)

    def ask(self, agent_id: str, prompt: str, *, user: str, context_scope: str = "reference") -> AgentResponse:
        """Process a user-initiated interaction by retrieving governed context and provenance."""
        agent = self.registry.require(agent_id)
        self.observations.record(agent, ObservationType.REQUEST, prompt)
        context = self.context_provider.retrieve(agent, context_scope)
        self.observations.record(agent, ObservationType.GRAPH_ACCESS, f"Read {context_scope}", scope=context_scope)
        self.memory.remember(agent, MemoryType.WORKING, prompt)
        output = (
            f"Agent {agent.label} inspected {context.triples} triples from {context_scope}. "
            "No autonomous business process was executed."
        )
        chain = self.provenance.record_execution(
            agent,
            request_user=user,
            graphs_accessed=[context_scope],
            output_text=output,
        )
        return AgentResponse(agent.agent_id, output, context_scope, context.triples, chain.execution)

    def use_tool(self, agent_id: str, tool_id: str, **kwargs: Any) -> Any:
        """Execute a governed tool for an approved agent."""
        agent = self.registry.require(agent_id)
        return self.tools.execute(agent, tool_id, **kwargs)
