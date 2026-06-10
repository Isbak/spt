"""Agent governance validation services."""

from __future__ import annotations

from dataclasses import dataclass

from semantic_platform.agents.registry import AgentRecord, AgentRegistry, AgentStatus


@dataclass(frozen=True)
class AgentGovernanceReport:
    """Governance validation report for registered agents."""

    managed_agents: int
    approved_agents: int
    errors: tuple[str, ...]

    @property
    def conforms(self) -> bool:
        """Return whether all registered agents are governed."""
        return not self.errors


def validate_agent_governance(registry: AgentRegistry | None = None) -> AgentGovernanceReport:
    """Validate ownership, stewardship, lifecycle status, and access controls."""
    registry = registry or AgentRegistry()
    agents = registry.list_agents()
    errors = registry.validate()
    return AgentGovernanceReport(
        managed_agents=len(agents),
        approved_agents=sum(1 for agent in agents if agent.status == AgentStatus.APPROVED),
        errors=tuple(errors),
    )


def require_approved(agent: AgentRecord) -> None:
    """Raise if an agent is not approved for runtime interactions."""
    if agent.status != AgentStatus.APPROVED:
        raise PermissionError(f"Agent {agent.agent_id} is not approved: {agent.status.value}")
