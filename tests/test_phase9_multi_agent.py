from rdflib import Graph, URIRef
from rdflib.namespace import PROV, RDF

from app.app import create_app
from semantic_platform.analytics import collaboration_metrics
from semantic_platform.graph import load_graph
from semantic_platform.multi_agent.accountability import AccountabilityLog
from semantic_platform.multi_agent.conflict import ConflictResolutionService
from semantic_platform.multi_agent.collaboration import CollaborationService
from semantic_platform.multi_agent.consensus import ConsensusMethod, ConsensusService
from semantic_platform.multi_agent.conversations import ConversationLog
from semantic_platform.multi_agent.delegation import DelegationService
from semantic_platform.multi_agent.explainability import CollaborationExplainer
from semantic_platform.multi_agent.memory import MemoryType, SharedSemanticMemory
from semantic_platform.multi_agent.negotiation import NegotiationService
from semantic_platform.multi_agent.teams import AgentTeamRegistry
from semantic_platform.multi_agent.common import MA


def test_agent_team_registry_rdf_assets_and_governance():
    graph = load_graph()
    teams = AgentTeamRegistry(graph).list_teams()
    assert teams
    assert teams[0].owner
    assert "PlannerAgent" in teams[0].roles
    assert AgentTeamRegistry(graph).validate_governance() == []
    assert (URIRef(MA["collaboration-team"]), RDF.type, MA.AgentTeam) in graph


def test_delegation_memory_conversation_and_accountability_provenance():
    graph = Graph()
    delegations = DelegationService(graph)
    task = delegations.create_task("goal-1", "Research governed option")
    delegation = delegations.delegate(task, "PlannerAgent", "ResearchAgent", "Research evidence", team="collaboration-team")
    assert delegation.governed
    assert (URIRef(delegation.uri), PROV.wasGeneratedBy, None) in graph

    memory = SharedSemanticMemory(graph).write(MemoryType.WORKING, "Current state", "Research assigned", actor="ObserverAgent", references=(task,))
    assert memory.memory_type == "SharedWorkingMemory"

    conversations = ConversationLog(graph)
    conversation = conversations.start("Task discussion", ("PlannerAgent", "ResearchAgent"))
    message = conversations.add_message(conversation, "ResearchAgent", "clarification", "Need semantic evidence.")
    assert message.content == "Need semantic evidence."
    assert conversations.messages(conversation)

    accountability = AccountabilityLog(graph).record("ResearchAgent", "collaboration-team", "ResearchAgent", task, "Assigned")
    assert accountability.actor.endswith("ResearchAgent")

    plan = CollaborationService(graph).plan("goal-1", {task: "ResearchAgent"})
    assert plan.goal.endswith("goal-1")
    assert plan.agents == ("ResearchAgent",)


def test_negotiation_consensus_conflict_and_explainability():
    graph = Graph()
    negotiations = NegotiationService(graph)
    first = negotiations.recommend("ResearchAgent", "Option A", "More evidence", 0.7)
    second = negotiations.recommend("ValidationAgent", "Option B", "Lower risk", 0.9)
    negotiation = negotiations.negotiate([first.uri, second.uri])
    assert negotiation.selected == second.uri
    assert "Compromise" in negotiation.compromise

    consensus = ConsensusService(graph).decide(
        "Choose lower risk option",
        {"ResearchAgent": True, "ValidationAgent": True, "GovernanceAgent": True},
        method=ConsensusMethod.WEIGHTED,
        weights={"ResearchAgent": 1.0, "ValidationAgent": 1.0, "GovernanceAgent": 2.0},
    )
    assert consensus.approved
    explanation = CollaborationExplainer(graph).explain(consensus.uri)
    assert "Goal → Agents Involved" in explanation.text

    conflicts = ConflictResolutionService(graph)
    conflict = conflicts.detect(first.uri, second.uri, "recommendation", "Different recommendations")
    escalated = conflicts.escalate(conflict.uri, "GovernanceAgent", "Needs governance review")
    assert escalated.status == "Escalated"
    resolved = conflicts.resolve(conflict.uri, "Accept lower risk option")
    assert resolved.status == "Resolved"


def test_collaboration_metrics_api_and_dashboard_routes():
    graph = load_graph()
    metrics = collaboration_metrics(graph)
    assert metrics["team_count"] >= 1

    client = create_app().test_client()
    for path in [
        "/api/agent-teams",
        "/api/delegations",
        "/api/conversations",
        "/api/negotiations",
        "/api/consensus",
        "/api/conflicts",
        "/agent-teams",
        "/delegations",
        "/conversations",
        "/negotiations",
        "/consensus",
        "/conflicts",
        "/collaboration-dashboard",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path
