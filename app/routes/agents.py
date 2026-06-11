"""Agent integration layer API and UI routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from semantic_platform.agents.agent import AgentRuntime
from semantic_platform.agents.governance import validate_agent_governance
from semantic_platform.api import explain_with_agent
from semantic_platform.agents.memory import AgentMemoryStore
from semantic_platform.agents.observations import AgentObservationLog
from semantic_platform.agents.provenance import AgentProvenanceRecorder
from semantic_platform.agents.registry import AgentRegistry

agents_bp = Blueprint("agents", __name__)
_registry = AgentRegistry()
_memory = AgentMemoryStore()
_observations = AgentObservationLog()
_provenance = AgentProvenanceRecorder()
_runtime = AgentRuntime(
    registry=_registry,
    memory=_memory,
    observations=_observations,
    provenance=_provenance,
)


def _agent_dict(agent):
    return {
        "id": agent.agent_id,
        "uri": agent.uri,
        "label": agent.label,
        "owner": agent.owner,
        "steward": agent.steward,
        "version": agent.version,
        "status": agent.status.value,
        "capabilities": list(agent.capabilities),
        "allowed_graphs": list(agent.allowed_graphs),
        "allowed_tools": list(agent.allowed_tools),
    }


@agents_bp.get("/api/agents")
def api_agents():
    """List registered governed agents."""
    return jsonify([_agent_dict(agent) for agent in _registry.list_agents()])


@agents_bp.get("/api/agents/<agent_id>")
def api_agent(agent_id: str):
    """Return a single governed agent."""
    return jsonify(_agent_dict(_registry.require(agent_id)))


@agents_bp.get("/api/agents/<agent_id>/context")
def api_agent_context(agent_id: str):
    """Return governed context metadata for an agent."""
    scope = request.args.get("scope", "reference")
    response = _runtime.ask(agent_id, f"Retrieve {scope} context", user="api", context_scope=scope)
    return jsonify(response.__dict__)


@agents_bp.get("/api/agents/<agent_id>/explain")
def api_agent_explain(agent_id: str):
    """Governed, read-only LLM assist: explain data the agent is permitted to read.

    Returns 403 when the agent may not read the requested scope.
    """
    scope = request.args.get("scope", "reference")
    question = request.args.get("question", f"Summarize the {scope} scope")
    try:
        result = explain_with_agent(agent_id, scope, question)
    except PermissionError as exc:
        return jsonify({"error": str(exc), "agent_id": agent_id, "scope": scope}), 403
    return jsonify(
        {
            "agent_id": result.agent_id,
            "scope": result.scope,
            "question": result.question,
            "provider": result.provider,
            "model": result.model_id,
            "fact_count": result.fact_count,
            "explanation_iri": result.explanation_iri,
            "text": result.text,
        }
    )


@agents_bp.get("/api/agents/<agent_id>/memory")
def api_agent_memory(agent_id: str):
    """Return agent memory records."""
    agent = _registry.require(agent_id)
    return jsonify([entry.__dict__ | {"memory_type": entry.memory_type.value, "created_at": entry.created_at.isoformat()} for entry in _memory.recall(agent)])


@agents_bp.get("/api/agents/<agent_id>/observations")
def api_agent_observations(agent_id: str):
    """Return agent observation records and metrics."""
    events = [event.__dict__ | {"event_type": event.event_type.value, "timestamp": event.timestamp.isoformat()} for event in _observations.observations(agent_id)]
    return jsonify({"events": events, "metrics": _observations.metrics()})


@agents_bp.get("/api/agents/<agent_id>/provenance")
def api_agent_provenance(agent_id: str):
    """Return agent provenance chains."""
    agent = _registry.require(agent_id)
    return jsonify([chain.__dict__ | {"timestamp": chain.timestamp.isoformat()} for chain in _provenance.chains(agent)])


@agents_bp.get("/agents")
def agents_home():
    """Render agent layer overview."""
    return render_template("agents.html", agents=_registry.list_agents(), metrics=_observations.metrics())


@agents_bp.get("/agent-registry")
def agent_registry_view():
    """Render agent registry."""
    return render_template("agent_registry.html", agents=_registry.list_agents())


@agents_bp.get("/agent-governance")
def agent_governance_view():
    """Render agent governance status."""
    return render_template("agent_governance.html", report=validate_agent_governance(_registry), agents=_registry.list_agents())


@agents_bp.get("/agent-memory")
def agent_memory_view():
    """Render agent memory stores."""
    rows = []
    for agent in _registry.list_agents():
        rows.extend(_memory.recall(agent))
    return render_template("agent_memory.html", rows=rows)


@agents_bp.get("/agent-observations")
def agent_observations_view():
    """Render agent observations and metrics."""
    return render_template("agent_observations.html", events=_observations.observations(), metrics=_observations.metrics())


@agents_bp.get("/agent-provenance")
def agent_provenance_view():
    """Render agent provenance chains."""
    chains = []
    for agent in _registry.list_agents():
        chains.extend(_provenance.chains(agent))
    return render_template("agent_provenance.html", chains=chains)
