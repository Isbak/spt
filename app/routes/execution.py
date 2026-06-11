"""Governed execution API and dashboard routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template
from rdflib import URIRef

from semantic_platform.execution.approvals import ExecutionApprovalEngine
from semantic_platform.execution.common import EXEC
from semantic_platform.execution.executor import GovernedExecutor
from semantic_platform.execution.registry import ExecutionRegistry
from semantic_platform.execution.risk import RiskClassifier
from semantic_platform.execution.rollback import RollbackService
from semantic_platform.execution.verification import VerificationService
from semantic_platform.graph import load_graph

execution_bp = Blueprint("execution", __name__)


def _graph():
    return load_graph()


def _prepared_graph():
    graph = _graph()
    approvals = ExecutionApprovalEngine(graph)
    action = URIRef(EXEC["update-resource-action"])
    if approvals.approved_count(action) == 0:
        approval = approvals.request(action, "execution-api", "human-steward")
        approvals.approve(approval.uri, "human-steward", "API sample approval")
    return graph


@execution_bp.get("/api/execution/actions")
def api_execution_actions():
    return jsonify([record.__dict__ for record in ExecutionRegistry(_graph()).list_actions()])


@execution_bp.get("/api/execution/approvals")
def api_execution_approvals():
    graph = _prepared_graph()
    return jsonify([record.__dict__ for record in ExecutionApprovalEngine(graph).list_approvals()])


@execution_bp.get("/api/execution/outcomes")
def api_execution_outcomes():
    graph = _prepared_graph()
    executor = GovernedExecutor(graph)
    execution = executor.execute(URIRef(EXEC["update-resource-action"]), policy=URIRef(EXEC["default-execution-policy"]))
    return jsonify([executor.outcomes.get(execution.outcome).__dict__])


@execution_bp.get("/api/execution/rollback")
def api_execution_rollback():
    graph = _prepared_graph()
    executor = GovernedExecutor(graph)
    execution = executor.execute(URIRef(EXEC["update-resource-action"]), policy=URIRef(EXEC["default-execution-policy"]))
    rollback = RollbackService(graph).rollback(execution.uri, URIRef(EXEC["update-resource-action"]), {"reason": "dashboard sample"})
    return jsonify(rollback.__dict__)


@execution_bp.get("/api/execution/verification")
def api_execution_verification():
    graph = _prepared_graph()
    executor = GovernedExecutor(graph)
    execution = executor.execute(URIRef(EXEC["update-resource-action"]), policy=URIRef(EXEC["default-execution-policy"]))
    return jsonify([record.__dict__ for record in VerificationService(graph).list_verifications() if record.outcome == execution.outcome])


@execution_bp.get("/api/execution")
def api_execution():
    graph = _prepared_graph()
    executor = GovernedExecutor(graph)
    execution = executor.execute(URIRef(EXEC["update-resource-action"]), policy=URIRef(EXEC["default-execution-policy"]))
    return jsonify({"executions": [execution.__dict__], "actions": [a.__dict__ for a in ExecutionRegistry(graph).list_actions()]})


@execution_bp.get("/execution")
def execution_view():
    data = api_execution().get_json()
    return render_template("execution.html", executions=data["executions"], actions=data["actions"])


@execution_bp.get("/execution-actions")
def execution_actions_view():
    return render_template("execution_actions.html", actions=api_execution_actions().get_json())


@execution_bp.get("/execution-history")
def execution_history_view():
    return render_template("execution_history.html", executions=api_execution().get_json()["executions"])


@execution_bp.get("/execution-approvals")
def execution_approvals_view():
    return render_template("execution_approvals.html", approvals=api_execution_approvals().get_json())


@execution_bp.get("/execution-outcomes")
def execution_outcomes_view():
    return render_template("execution_outcomes.html", outcomes=api_execution_outcomes().get_json())


@execution_bp.get("/execution-risk")
def execution_risk_view():
    classifier = RiskClassifier()
    actions = api_execution_actions().get_json()
    risks = [record | {"audit_required": classifier.classify(record["action_type"], declared=record["risk"]).audit_required} for record in actions]
    return render_template("execution_risk.html", risks=risks)


@execution_bp.get("/execution-rollback")
def execution_rollback_view():
    graph = _graph()
    return render_template("execution_rollback.html", plans=[p.__dict__ for p in RollbackService(graph).list_plans()])
