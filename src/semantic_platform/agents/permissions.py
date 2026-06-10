"""Agent graph and tool permission model.

The permission model intentionally separates read and write graph scopes. Agents may read
governed platform graphs when registered for those scopes, but writes are limited to sandbox
and integration graphs unless an explicit approval flag is supplied by a governing API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class GraphScope(StrEnum):
    """Named graph access scopes available to agents."""

    ONTOLOGY = "ontology"
    REFERENCE = "reference"
    GOVERNANCE = "governance"
    PROVENANCE = "provenance"
    REASONING = "reasoning"
    SANDBOX = "sandbox"
    INTEGRATION = "integration"


READ_SCOPES = frozenset(
    {
        GraphScope.ONTOLOGY,
        GraphScope.REFERENCE,
        GraphScope.GOVERNANCE,
        GraphScope.PROVENANCE,
        GraphScope.REASONING,
    }
)
WRITE_SCOPES = frozenset({GraphScope.SANDBOX, GraphScope.INTEGRATION})
PROTECTED_WRITE_SCOPES = frozenset({GraphScope.ONTOLOGY, GraphScope.GOVERNANCE, GraphScope.PROVENANCE})


@dataclass(frozen=True)
class PermissionSet:
    """Read, write, and tool permissions assigned to a registered agent."""

    read_graphs: frozenset[str] = field(default_factory=frozenset)
    write_graphs: frozenset[str] = field(default_factory=frozenset)
    tools: frozenset[str] = field(default_factory=frozenset)

    def can_read(self, graph_scope: str) -> bool:
        """Return whether the agent can read a graph scope."""
        return graph_scope in self.read_graphs

    def can_write(self, graph_scope: str, *, approved: bool = False) -> bool:
        """Return whether the agent can write a graph scope.

        Protected governance, provenance, and ontology writes require an explicit approval flag
        and an assigned write permission. Ordinary agent operation should not set that flag.
        """
        if graph_scope in {scope.value for scope in PROTECTED_WRITE_SCOPES}:
            return approved and graph_scope in self.write_graphs
        return graph_scope in self.write_graphs and graph_scope in {scope.value for scope in WRITE_SCOPES}

    def can_use_tool(self, tool_id: str) -> bool:
        """Return whether the agent can use a registered tool."""
        return tool_id in self.tools


def default_read_permissions() -> frozenset[str]:
    """Return the default read scopes for governed semantic context."""
    return frozenset(scope.value for scope in READ_SCOPES)


def default_write_permissions() -> frozenset[str]:
    """Return the safe default write scopes for agents."""
    return frozenset(scope.value for scope in WRITE_SCOPES)
