"""Knowledge Model tree: the shared views mounted under ``/model/<domain_id>/``.

Each blueprint mirrors a System blueprint with a ``model_`` prefix and identical endpoint
names, so :meth:`app.context_scope.ContextScope.url_for` rewrites System links into this
tree by simply prefixing ``model_`` and supplying ``domain_id``. The active domain scope
is bound to ``g.scope`` by the app factory's ``before_request`` (from the ``domain_id`` in
the URL), so handlers consume ``domain_id`` only to satisfy the route and otherwise defer
to the shared render functions.
"""

from __future__ import annotations

from flask import Blueprint

from app.views import domain_models as domain_models_view
from app.views import governance as governance_view
from app.views import graph as graph_view
from app.views import named_graphs as named_graphs_view
from app.views import ontology as ontology_view
from app.views import ontology_version as ontology_version_view
from app.views import provenance as provenance_view
from app.views import query as query_view
from app.views import reasoning as reasoning_view

#: URL prefix carrying the active domain; ``before_request`` reads it into ``g.scope``.
_PREFIX = "/model/<domain_id>"


def _bp(name: str, suffix: str) -> Blueprint:
    """Return a ``model_<name>`` blueprint mounted under ``/model/<domain_id>{suffix}``."""
    return Blueprint(f"model_{name}", __name__, url_prefix=f"{_PREFIX}{suffix}")


def _mount(bp: Blueprint, endpoint: str, render, *, methods: list[str] | None = None) -> None:
    """Bind a shared render function as ``endpoint``, ignoring the URL ``domain_id``."""
    bp.add_url_rule(
        "", endpoint, lambda domain_id: render(), methods=methods or ["GET"]
    )


# --- Knowledge Graph angles -------------------------------------------------
ontology_bp = _bp("ontology", "/ontology")
_mount(ontology_bp, "index", ontology_view.text)

graph_bp = _bp("graph", "/graphs")
_mount(graph_bp, "index", graph_view.stats)

domain_models_bp = _bp("domain_models", "/domain-models")
_mount(domain_models_bp, "index", domain_models_view.domain_models)

shapes_bp = _bp("shapes", "/shapes")
_mount(shapes_bp, "index", domain_models_view.shapes)

named_graphs_bp = _bp("named_graphs", "/named-graphs")
_mount(named_graphs_bp, "index", named_graphs_view.index)

ontology_version_bp = _bp("ontology_version", "/ontology-version")
_mount(ontology_version_bp, "index", ontology_version_view.index)

# --- Query & search ---------------------------------------------------------
query_bp = _bp("query", "/query")
_mount(query_bp, "index", query_view.index, methods=["GET", "POST"])

# --- Governance & provenance ------------------------------------------------
governance_bp = _bp("governance", "/governance")
_mount(governance_bp, "index", governance_view.summary)

provenance_bp = _bp("provenance", "/provenance")
_mount(provenance_bp, "index", provenance_view.summary)

# --- Reasoning --------------------------------------------------------------
reasoning_bp = _bp("reasoning", "")
reasoning_bp.add_url_rule("/reasoning", "reasoning_index", lambda domain_id: reasoning_view.index())
reasoning_bp.add_url_rule("/inferences", "inferences_index", lambda domain_id: reasoning_view.inferences())
reasoning_bp.add_url_rule(
    "/legacy-explanations", "explanations_index", lambda domain_id: reasoning_view.legacy_explanations()
)
reasoning_bp.add_url_rule("/consistency", "consistency_index", lambda domain_id: reasoning_view.consistency())
reasoning_bp.add_url_rule("/rules", "rules_index", lambda domain_id: reasoning_view.rules())

# --- Visualization (multi-endpoint, mirrors the System ``visualization`` bp) -
visualization_bp = _bp("visualization", "")
visualization_bp.add_url_rule("/graph", "graph_explorer", lambda domain_id: graph_view.explorer())
visualization_bp.add_url_rule("/graph/node", "graph_node", lambda domain_id: graph_view.node())
visualization_bp.add_url_rule("/ontology-browser", "ontology_browser", lambda domain_id: ontology_view.browser())
visualization_bp.add_url_rule(
    "/governance-dashboard", "governance_dashboard", lambda domain_id: governance_view.dashboard()
)
visualization_bp.add_url_rule(
    "/provenance-explorer", "provenance_explorer", lambda domain_id: provenance_view.explorer()
)
visualization_bp.add_url_rule(
    "/reasoning-dashboard", "reasoning_dashboard", lambda domain_id: reasoning_view.dashboard()
)
visualization_bp.add_url_rule("/explanations", "explanations", lambda domain_id: reasoning_view.explanations())
visualization_bp.add_url_rule("/analytics", "analytics", lambda domain_id: reasoning_view.analytics())
visualization_bp.add_url_rule(
    "/search", "search", lambda domain_id: query_view.search(), methods=["GET", "POST"]
)


def knowledge_model_blueprints() -> list[Blueprint]:
    """Return every Knowledge Model blueprint for registration by the app factory."""
    return [
        ontology_bp,
        graph_bp,
        domain_models_bp,
        shapes_bp,
        named_graphs_bp,
        ontology_version_bp,
        query_bp,
        governance_bp,
        provenance_bp,
        reasoning_bp,
        visualization_bp,
    ]
