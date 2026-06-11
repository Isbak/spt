from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from app.app import create_app
from semantic_platform.execution.actions import ActionCatalog
from semantic_platform.execution.approvals import ExecutionApprovalEngine
from semantic_platform.execution.common import EXEC
from semantic_platform.execution.executor import GovernedExecutor
from semantic_platform.execution.explainability import ExecutionExplainer
from semantic_platform.execution.policies import ExecutionPolicyEngine
from semantic_platform.execution.registry import ExecutionRegistry
from semantic_platform.execution.risk import RiskClassifier, RiskLevel
from semantic_platform.execution.rollback import RollbackService
from semantic_platform.execution.verification import VerificationService
from semantic_platform.graph import load_graph
from semantic_platform.orchestration.policies import PolicyEvaluator


def test_execution_registry_rdf_assets_and_risk():
    graph = load_graph()
    actions = ExecutionRegistry(graph).list_actions()
    assert len(actions) >= 8
    assert {a.status for a in actions} >= {"Draft", "Testing", "Approved", "Restricted", "Retired"}
    assert (URIRef(EXEC["create-resource-action"]), RDF.type, EXEC.ExecutionAction) in graph
    risk = RiskClassifier().classify("Delete Resource", "REST API")
    assert risk.level == RiskLevel.HIGH
    assert risk.approvals_required == 2


def test_policy_approval_execution_verification_explainability_and_provenance():
    graph = Graph()
    catalog = ActionCatalog(graph)
    target = catalog.create_target("REST", "REST API")
    action = catalog.create_action("Update", "Update Resource", target.uri, risk=RiskLevel.MEDIUM, approval_required=1)
    policy = ExecutionPolicyEngine(graph).create_policy("Default", max_risk=RiskLevel.HIGH)

    executor = GovernedExecutor(graph)
    try:
        executor.execute(action.uri, policy=policy)
    except PermissionError as exc:
        assert "approval" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("execution without approval should fail")

    approvals = ExecutionApprovalEngine(graph)
    approval = approvals.request(action.uri, "agent", "human")
    approvals.approve(approval.uri, "human")
    execution = executor.execute(action.uri, policy=policy, goal="https://example.org/goal", workflow="https://example.org/workflow", plan="https://example.org/plan")

    assert execution.status == "Succeeded"
    outcome = executor.outcomes.get(execution.outcome)
    assert outcome.verified
    assert VerificationService(graph).list_verifications()
    explanation = ExecutionExplainer(graph).explain(execution.uri)
    assert "Goal → Workflow → Plan" in explanation.text
    assert (URIRef(execution.uri), EXEC.executedAction, URIRef(action.uri)) in graph


def test_rollback_supported_and_not_supported():
    graph = Graph()
    catalog = ActionCatalog(graph)
    target = catalog.create_target("Queue", "Message Queue")
    action = catalog.create_action("Publish", "Publish Message", target.uri, rollback_supported=False)
    policy = ExecutionPolicyEngine(graph).create_policy("Default")
    execution = GovernedExecutor(graph).execute(action.uri, policy=policy)
    plan = RollbackService(graph).declare_plan(action.uri, False, "Published messages cannot be withdrawn")
    rollback = RollbackService(graph).rollback(execution.uri, action.uri)

    assert not plan.supported
    assert rollback.status == "RollbackFailed"


def test_policy_denies_disallowed_execution_and_orchestration_extension():
    graph = Graph()
    catalog = ActionCatalog(graph)
    target = catalog.create_target("Database", "Database Procedure")
    action = catalog.create_action("Delete", "Delete Resource", target.uri, risk=RiskLevel.CRITICAL)
    policy = ExecutionPolicyEngine(graph).create_policy("Low only", max_risk=RiskLevel.LOW, allowed_targets=("REST API",))
    decision = ExecutionPolicyEngine(graph).evaluate(action, "Database Procedure", policy)
    assert not decision.allowed
    assert not PolicyEvaluator(graph).evaluate_execution(action, "Database Procedure", policy).allowed


def test_execution_api_and_dashboard_routes():
    client = create_app().test_client()
    for path in [
        "/api/execution",
        "/api/execution/actions",
        "/api/execution/approvals",
        "/api/execution/outcomes",
        "/api/execution/rollback",
        "/api/execution/verification",
        "/execution",
        "/execution-actions",
        "/execution-history",
        "/execution-approvals",
        "/execution-outcomes",
        "/execution-risk",
        "/execution-rollback",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path
