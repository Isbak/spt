"""Semantic orchestration API and dashboard routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from semantic_platform.analytics import orchestration_metrics
from semantic_platform.graph import load_graph
from semantic_platform.orchestration.approvals import ApprovalWorkflow
from semantic_platform.orchestration.events import EventLog
from semantic_platform.orchestration.execution_plan import ExecutionPlanBuilder
from semantic_platform.orchestration.goals import GoalManager
from semantic_platform.orchestration.registry import OrchestrationRegistry
from rdflib import URIRef
from rdflib.namespace import RDF

from semantic_platform.orchestration.common import ORCH

orchestration_bp = Blueprint("orchestration", __name__)


def _graph():
    return load_graph()


def _workflows():
    return [record.__dict__ | {"approval_status": record.approval_status.value} for record in OrchestrationRegistry(graph=_graph()).list_workflows()]


@orchestration_bp.get("/api/goals")
def api_goals():
    graph = _graph()
    goals = GoalManager(graph)
    rows = [goals.get_goal(goal).__dict__ for goal in graph.subjects(RDF.type, ORCH.Goal)]
    # Most repository data focuses on workflow templates; expose a governed sample when no goals are persisted.
    if not rows:
        rows = [goals.create_goal("Govern semantic coordination readiness").__dict__]
    return jsonify(rows)


@orchestration_bp.get("/api/workflows")
def api_workflows():
    return jsonify(_workflows())


@orchestration_bp.get("/api/events")
def api_events():
    log = EventLog(_graph())
    if not log.events():
        log.record_event("Graph Updated", "semantic-platform", "Knowledge graph assets loaded")
    return jsonify([event.__dict__ for event in log.events()])


@orchestration_bp.get("/api/approvals")
def api_approvals():
    graph = _graph()
    approvals = ApprovalWorkflow(graph)
    rows = [approvals._record(approval).__dict__ for approval in graph.subjects(RDF.type, ORCH.ApprovalGate)]
    if not rows:
        rows = [approvals.request(URIRef("https://example.org/semantic-platform/orchestration#approval-workflow"), "orchestration-api", "human-steward").__dict__]
    return jsonify(rows)


@orchestration_bp.get("/api/execution-plans")
def api_execution_plans():
    graph = _graph()
    tasks = list(graph.objects(URIRef("https://example.org/semantic-platform/orchestration#multi-step-workflow"), ORCH.decomposesInto))
    builder = ExecutionPlanBuilder(graph)
    goal = GoalManager(graph).create_goal("Coordinate multi-step workflow")
    plan = builder.build_plan(goal.uri, tasks)
    return jsonify([plan.__dict__])


@orchestration_bp.get("/api/orchestration")
def api_orchestration():
    return jsonify({"metrics": orchestration_metrics(_graph()), "workflows": _workflows()})


@orchestration_bp.get("/goal-management")
def goal_management_view():
    goals = api_goals().get_json()
    return render_template("goal_management.html", goals=goals)


@orchestration_bp.get("/workflows")
def workflows_view():
    return render_template("workflows.html", workflows=OrchestrationRegistry(graph=_graph()).list_workflows())


@orchestration_bp.get("/execution-plans")
def execution_plans_view():
    plans = api_execution_plans().get_json()
    return render_template("execution_plans.html", plans=plans)


@orchestration_bp.get("/events")
def events_view():
    events = api_events().get_json()
    return render_template("events.html", events=events)


@orchestration_bp.get("/approvals")
def approvals_view():
    approvals = api_approvals().get_json()
    return render_template("approvals.html", approvals=approvals)


@orchestration_bp.get("/orchestration-dashboard")
def orchestration_dashboard_view():
    return render_template("orchestration_dashboard.html", metrics=orchestration_metrics(_graph()), workflows=OrchestrationRegistry(graph=_graph()).list_workflows())


@orchestration_bp.get("/orchestration-explanations")
def orchestration_explanations_view():
    return render_template("orchestration_explanations.html", explanations=[{"text": "Recommendations explain goals, inputs, dependencies, policies, and approvals before any execution."}])
