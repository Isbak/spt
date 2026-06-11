from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from app.app import create_app
from semantic_platform.analytics import orchestration_metrics
from semantic_platform.orchestration.approvals import ApprovalWorkflow
from semantic_platform.orchestration.common import ORCH
from semantic_platform.orchestration.coordination import CoordinationService
from semantic_platform.orchestration.events import EventLog
from semantic_platform.orchestration.execution_plan import ExecutionPlanBuilder
from semantic_platform.orchestration.explainability import ExplanationService
from semantic_platform.orchestration.goals import GoalManager
from semantic_platform.orchestration.planner import OrchestrationPlanner
from semantic_platform.orchestration.policies import PolicyEvaluator
from semantic_platform.orchestration.registry import LifecycleStatus, OrchestrationRegistry
from semantic_platform.orchestration.workflows import WorkflowEngine, WorkflowState


def test_goal_creation_objectives_mapping_and_progress():
    goals = GoalManager()
    goal = goals.create_goal("Improve semantic coordination")
    objective = goals.register_objective(goal.uri, "Coordinate tasks")
    task = URIRef("https://example.org/task/1")
    goals.map_task_to_goal(task, goal.uri, complete=True)

    record = goals.get_goal(goal.uri)
    assert objective
    assert record.progress == 1.0
    assert (URIRef(goal.uri), RDF.type, ORCH.Goal) in goals.graph


def test_workflow_registration_dependency_validation_and_registry():
    engine = WorkflowEngine()
    workflow = engine.define_workflow("Review workflow", ["Prepare", "Review"], state=WorkflowState.READY)
    first, second = workflow.tasks
    engine.add_dependency(second, first)

    assert not engine.validate_workflow(workflow.uri)
    assert engine.dependency_graph(workflow.uri)[second] == {first}

    registry = OrchestrationRegistry(graph=engine.graph)
    registered = registry.require(workflow.uri)
    assert registered.approval_status == LifecycleStatus.DRAFT
    assert not registry.validate()


def test_execution_plan_generation_dependency_ordering_and_provenance():
    graph = Graph()
    builder = ExecutionPlanBuilder(graph)
    goal = URIRef("https://example.org/goal")
    graph.add((goal, RDF.type, ORCH.Goal))
    graph.add((goal, ORCH.status, Literal("Active")))
    task_a = URIRef("https://example.org/task/a")
    task_b = URIRef("https://example.org/task/b")
    graph.add((task_b, ORCH.dependsOn, task_a))

    plan = builder.build_plan(goal, [task_b, task_a])

    assert plan.tasks == (str(task_a), str(task_b))
    assert not plan.ready
    assert (URIRef(plan.uri), RDF.type, ORCH.ExecutionPlan) in graph


def test_events_policies_approvals_coordination_and_explanations():
    graph = Graph()
    events = EventLog(graph)
    event = events.record_event("Agent Completed Task", "agent", "Task ready for review")
    assert events.events()[0].uri == event.uri

    policies = PolicyEvaluator(graph)
    policy = policies.create_policy("Approval required")
    workflow = URIRef("https://example.org/workflow")
    graph.add((workflow, ORCH.governedByPolicy, policy))
    decision = policies.evaluate(workflow)
    assert decision.allowed
    assert decision.approvals_required == (str(policy),)

    approvals = ApprovalWorkflow(graph)
    approval = approvals.request(workflow, "requester", "reviewer")
    reviewed = approvals.review(approval.uri, "reviewer", "Approved", "ok")
    assert reviewed.status == "Approved"

    coordination = CoordinationService(graph)
    recommendation = coordination.recommend_assignment(URIRef("https://example.org/task"), "human-reviewer", "Human", "Requires judgement")
    explanation = ExplanationService(graph).explain(recommendation.uri, goal="Coordinate", inputs=[event.uri], dependencies=[], policies=[str(policy)], approvals=[approval.uri])
    assert "Approvals required" in explanation.text


def test_policy_aware_planner_proposes_plan_without_execution():
    graph = Graph()
    planner = OrchestrationPlanner(graph)
    policy = planner.policies.create_policy("Default")
    workflow = URIRef("https://example.org/workflow")
    goal = URIRef("https://example.org/goal")
    task = URIRef("https://example.org/task")
    graph.add((workflow, ORCH.governedByPolicy, policy))
    graph.add((goal, RDF.type, ORCH.Goal))
    graph.add((goal, ORCH.status, Literal("Active")))

    result = planner.propose_plan(goal, workflow, [task])
    assert result.policy_decision.allowed
    assert not result.plan.ready


def test_orchestration_metrics_registry_and_routes():
    registry = OrchestrationRegistry()
    assert registry.list_workflows()
    metrics = orchestration_metrics()
    assert metrics["workflow_count"] >= 4
    assert metrics["dependency_count"] >= 4

    client = create_app().test_client()
    for path in [
        "/api/goals",
        "/api/workflows",
        "/api/events",
        "/api/approvals",
        "/api/execution-plans",
        "/api/orchestration",
        "/goal-management",
        "/workflows",
        "/execution-plans",
        "/events",
        "/approvals",
        "/orchestration-dashboard",
        "/orchestration-explanations",
    ]:
        assert client.get(path).status_code == 200
