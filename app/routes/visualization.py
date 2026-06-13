"""Phase 5 semantic exploration and visualization routes (System tree).

View logic lives in the shared :mod:`app.views` modules so the System and Knowledge
Model trees render identically over their respective contexts.
"""

from __future__ import annotations

from flask import Blueprint

from app.views import graph as graph_view
from app.views import governance as governance_view
from app.views import ontology as ontology_view
from app.views import provenance as provenance_view
from app.views import query as query_view
from app.views import reasoning as reasoning_view

visualization_bp = Blueprint("visualization", __name__)


@visualization_bp.get("/graph")
def graph_explorer():
    """Render interactive knowledge graph exploration."""
    return graph_view.explorer()


@visualization_bp.get("/graph/node")
def graph_node():
    """Return JSON detail for one graph node (right-hand inspector sidebar)."""
    return graph_view.node()


@visualization_bp.get("/ontology-browser")
def ontology_browser():
    """Render ontology hierarchy, property, and instance browser."""
    return ontology_view.browser()


@visualization_bp.get("/governance-dashboard")
def governance_dashboard():
    """Render governance oversight dashboard."""
    return governance_view.dashboard()


@visualization_bp.get("/provenance-explorer")
def provenance_explorer():
    """Render provenance lineage explorer."""
    return provenance_view.explorer()


@visualization_bp.get("/reasoning-dashboard")
def reasoning_dashboard():
    """Render reasoning explainability dashboard."""
    return reasoning_view.dashboard()


@visualization_bp.get("/explanations")
def explanations():
    """Render detailed inference explanations."""
    return reasoning_view.explanations()


@visualization_bp.get("/analytics")
def analytics():
    """Render graph analytics dashboard."""
    return reasoning_view.analytics()


@visualization_bp.route("/search", methods=["GET", "POST"])
def search():
    """Render semantic search over platform assets."""
    return query_view.search()
