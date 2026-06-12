"""Tests for ContextScope.url_for tree resolution and page-context mapping."""

from __future__ import annotations

from app.app import create_app
from app.context_scope import ContextScope, system_scope
from app.page_context import resolve_page_context
from semantic_platform.config import load_settings


def test_system_scope_url_for_uses_system_endpoints():
    app = create_app()
    with app.test_request_context():
        scope = system_scope(load_settings())
        assert scope.is_system
        assert scope.url_for("ontology.index") == "/ontology"
        assert scope.url_for("visualization.graph_explorer") == "/graph"


def test_domain_scope_url_for_rewrites_to_model_tree():
    app = create_app()
    with app.test_request_context():
        scope = ContextScope("field-service", "Field Service", load_settings(), is_system=False)
        assert scope.url_for("ontology.index") == "/model/field-service/ontology"
        assert (
            scope.url_for("visualization.graph_explorer")
            == "/model/field-service/graph"
        )


def test_page_context_strips_model_prefix_and_flags_context_aware():
    # KM endpoints resolve to the same scope as their System equivalents.
    assert resolve_page_context("model_ontology.index")["scope"] == "ontology"
    assert resolve_page_context("model_governance.index")["scope"] == "governance"
    # Dual-mounted views are context-aware; operational ones are not.
    assert resolve_page_context("ontology.index")["context_aware"] is True
    assert resolve_page_context("agents.agents_home")["context_aware"] is False
    # Active context id is echoed for the UI.
    assert resolve_page_context("ontology.index", "field-service")["context"] == "field-service"
