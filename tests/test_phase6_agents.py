from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS

from app.app import create_app
from semantic_platform.agents.context import AgentContextProvider
from semantic_platform.agents.governance import validate_agent_governance
from semantic_platform.agents.memory import AgentMemoryStore, MemoryType
from semantic_platform.agents.observations import AgentObservationLog, ObservationType
from semantic_platform.agents.permissions import PermissionSet
from semantic_platform.agents.planner import AgentPlanner
from semantic_platform.agents.provenance import AgentProvenanceRecorder
from semantic_platform.agents.registry import AGENT, AGGOV, AgentRegistry, AgentStatus
from semantic_platform.agents.safety import check_agent_action
from semantic_platform.agents.tools import AgentTool, AgentToolRegistry


def test_agent_registry_registration_and_lifecycle():
    registry = AgentRegistry()
    agent = registry.require("semantic-context-agent")

    assert agent.status == AgentStatus.APPROVED
    assert agent.owner
    assert "Semantic context retrieval" in agent.capabilities
    assert not registry.validate()


def test_agent_governance_ownership_and_permissions():
    report = validate_agent_governance(AgentRegistry())
    agent = AgentRegistry().require("semantic-context-agent")

    assert report.conforms
    assert agent.permissions.can_read("ontology")
    assert agent.permissions.can_write("sandbox")
    assert not agent.permissions.can_write("ontology")
    assert check_agent_action(agent, graph_scope="ontology").allowed
    assert not check_agent_action(agent, graph_scope="ontology", write=True).allowed


def test_permission_set_protected_write_requires_approval_and_assignment():
    permissions = PermissionSet(read_graphs=frozenset({"ontology"}), write_graphs=frozenset({"ontology"}))

    assert not permissions.can_write("ontology")
    assert permissions.can_write("ontology", approved=True)


def test_agent_context_retrieval():
    agent = AgentRegistry().require("semantic-context-agent")
    context = AgentContextProvider().ontology_context(agent)

    assert context.scope == "ontology"
    assert context.triples > 0


def test_agent_memory_storage_and_retrieval():
    agent = AgentRegistry().require("semantic-context-agent")
    store = AgentMemoryStore()
    entry = store.remember(agent, MemoryType.SESSION, "remember this", session_id="s1")

    recalled = store.recall(agent, MemoryType.SESSION)
    assert recalled[0].memory_id == entry.memory_id
    assert recalled[0].content == "remember this"
    assert recalled[0].session_id == "s1"


def test_agent_provenance_creation_and_queries():
    agent = AgentRegistry().require("semantic-context-agent")
    recorder = AgentProvenanceRecorder()
    chain = recorder.record_execution(agent, request_user="tester", tools_used=["semantic-search"], graphs_accessed=["reference"], output_text="ok")

    assert chain.execution
    assert recorder.chains(agent)[0].execution == chain.execution


def test_agent_observability_metrics():
    agent = AgentRegistry().require("semantic-context-agent")
    log = AgentObservationLog()
    log.record(agent, ObservationType.REQUEST, "hello")
    log.record(agent, ObservationType.WARNING, "careful")

    assert log.metrics()["requests"] == 1
    assert log.metrics()["warnings"] == 1


def test_tool_registration_and_execution():
    agent = AgentRegistry().require("semantic-context-agent")
    tools = AgentToolRegistry()
    tools.register(AgentTool("custom", "Custom", "reference", lambda value: value.upper()))
    # The custom tool is not assigned to the agent, so safety blocks it.
    try:
        tools.execute(agent, "custom", value="x")
    except PermissionError as exc:
        assert "tool access denied" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected custom tool to be denied")

    result = tools.execute(agent, "semantic-search", query="Dataset")
    assert isinstance(result, list)


def test_planner_creates_plan_without_execution():
    agent = AgentRegistry().require("semantic-context-agent")
    plan = AgentPlanner().plan(agent, "Answer question", ["Retrieve context", "Explain result"])

    assert plan.goal == "Answer question"
    assert plan.actions == ("Review task: Retrieve context", "Review task: Explain result")


def test_registry_validation_detects_unmanaged_agent():
    graph = Graph()
    graph.add((AGENT.unmanaged, RDF.type, AGENT.Agent))
    graph.add((AGENT.unmanaged, RDFS.label, Literal("Unmanaged")))
    graph.add((AGENT.unmanaged, AGGOV.approvalStatus, Literal("Draft")))
    registry = AgentRegistry(graph=graph)

    errors = registry.validate()
    assert any("no owner" in error for error in errors)
    assert any("no steward" in error for error in errors)


def test_agent_api_endpoints_and_views():
    app = create_app()
    client = app.test_client()

    assert client.get("/api/agents").status_code == 200
    assert client.get("/api/agents/semantic-context-agent").status_code == 200
    assert client.get("/api/agents/semantic-context-agent/context?scope=reference").status_code == 200
    assert client.get("/api/agents/semantic-context-agent/memory").status_code == 200
    assert client.get("/api/agents/semantic-context-agent/observations").status_code == 200
    assert client.get("/api/agents/semantic-context-agent/provenance").status_code == 200
    assert client.get("/agents").status_code == 200
    assert client.get("/agent-registry").status_code == 200
    assert client.get("/agent-governance").status_code == 200
    assert client.get("/agent-memory").status_code == 200
    assert client.get("/agent-observations").status_code == 200
    assert client.get("/agent-provenance").status_code == 200
