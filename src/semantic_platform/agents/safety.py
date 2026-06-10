"""Safety checks for governed agent interactions."""

from __future__ import annotations

from dataclasses import dataclass

from semantic_platform.agents.governance import require_approved
from semantic_platform.agents.registry import AgentRecord


@dataclass(frozen=True)
class SafetyDecision:
    """Result of a policy, graph, or tool access decision."""

    allowed: bool
    reason: str


def check_agent_action(
    agent: AgentRecord,
    *,
    graph_scope: str | None = None,
    write: bool = False,
    tool_id: str | None = None,
    approved_write: bool = False,
) -> SafetyDecision:
    """Evaluate whether an agent action is governed and safe."""
    try:
        require_approved(agent)
    except PermissionError as exc:
        return SafetyDecision(False, str(exc))

    if graph_scope and write and not agent.permissions.can_write(graph_scope, approved=approved_write):
        return SafetyDecision(False, f"write access denied for graph scope: {graph_scope}")
    if graph_scope and not write and not agent.permissions.can_read(graph_scope):
        return SafetyDecision(False, f"read access denied for graph scope: {graph_scope}")
    if tool_id and not agent.permissions.can_use_tool(tool_id):
        return SafetyDecision(False, f"tool access denied: {tool_id}")
    return SafetyDecision(True, "allowed")


def require_safe_action(**kwargs: object) -> None:
    """Raise ``PermissionError`` when ``check_agent_action`` denies an action."""
    decision = check_agent_action(**kwargs)  # type: ignore[arg-type]
    if not decision.allowed:
        raise PermissionError(decision.reason)
