"""Multi-agent collaboration API and dashboard routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from semantic_platform.analytics import collaboration_metrics
from semantic_platform.graph import load_graph
from semantic_platform.multi_agent.conflict import ConflictResolutionService
from semantic_platform.multi_agent.consensus import ConsensusMethod, ConsensusService
from semantic_platform.multi_agent.conversations import ConversationLog
from semantic_platform.multi_agent.delegation import DelegationService
from semantic_platform.multi_agent.negotiation import NegotiationService
from semantic_platform.multi_agent.teams import AgentTeamRegistry

multi_agent_bp = Blueprint("multi_agent", __name__)


def _graph():
    return load_graph()


def _sample_graph():
    graph = _graph()
    delegation = DelegationService(graph)
    task = delegation.create_task("phase-9-goal", "Assess collaboration readiness")
    delegation.delegate(task, "PlannerAgent", "ValidationAgent", "Validate multi-agent readiness", team="collaboration-team")
    conversations = ConversationLog(graph)
    conv = conversations.start("Collaboration readiness", ("PlannerAgent", "ValidationAgent"))
    conversations.add_message(conv, "PlannerAgent", "recommendation", "Use governed delegation and consensus.")
    negotiation = NegotiationService(graph)
    rec1 = negotiation.recommend("PlannerAgent", "Majority consensus", "Fast and auditable", 0.8)
    rec2 = negotiation.recommend("GovernanceAgent", "Governance-approved consensus", "Higher assurance", 0.9)
    negotiation.negotiate([rec1.uri, rec2.uri])
    ConsensusService(graph).decide("Use governance-approved consensus for sensitive collaboration", {"PlannerAgent": True, "GovernanceAgent": True}, method=ConsensusMethod.GOVERNANCE_APPROVED)
    ConflictResolutionService(graph).detect(rec1.uri, rec2.uri, "recommendation", "Different assurance preferences")
    return graph


@multi_agent_bp.get("/api/agent-teams")
def api_agent_teams():
    return jsonify([team.__dict__ for team in AgentTeamRegistry(graph=_graph()).list_teams()])


@multi_agent_bp.get("/api/delegations")
def api_delegations():
    return jsonify([delegation.__dict__ for delegation in DelegationService(_sample_graph()).delegations()])


@multi_agent_bp.get("/api/conversations")
def api_conversations():
    graph = _sample_graph()
    return jsonify([message.__dict__ for message in ConversationLog(graph).messages()])


@multi_agent_bp.get("/api/negotiations")
def api_negotiations():
    graph = _sample_graph()
    return jsonify([negotiation.__dict__ for negotiation in NegotiationService(graph).negotiations()])


@multi_agent_bp.get("/api/consensus")
def api_consensus():
    graph = _sample_graph()
    return jsonify([consensus.__dict__ for consensus in ConsensusService(graph).consensuses()])


@multi_agent_bp.get("/api/conflicts")
def api_conflicts():
    graph = _sample_graph()
    return jsonify([conflict.__dict__ for conflict in ConflictResolutionService(graph).conflicts()])


@multi_agent_bp.get("/agent-teams")
def agent_teams_view():
    return render_template("agent_teams.html", teams=AgentTeamRegistry(graph=_graph()).list_teams())


@multi_agent_bp.get("/delegations")
def delegations_view():
    return render_template("delegations.html", delegations=api_delegations().get_json())


@multi_agent_bp.get("/conversations")
def conversations_view():
    return render_template("conversations.html", messages=api_conversations().get_json())


@multi_agent_bp.get("/negotiations")
def negotiations_view():
    return render_template("negotiations.html", negotiations=api_negotiations().get_json())


@multi_agent_bp.get("/consensus")
def consensus_view():
    return render_template("consensus.html", consensuses=api_consensus().get_json())


@multi_agent_bp.get("/conflicts")
def conflicts_view():
    return render_template("conflicts.html", conflicts=api_conflicts().get_json())


@multi_agent_bp.get("/collaboration-dashboard")
def collaboration_dashboard_view():
    graph = _sample_graph()
    return render_template("collaboration_dashboard.html", metrics=collaboration_metrics(graph), teams=AgentTeamRegistry(graph=graph).list_teams(), delegations=DelegationService(graph).delegations(), conflicts=ConflictResolutionService(graph).conflicts())
