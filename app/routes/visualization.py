"""Phase 5 semantic exploration and visualization routes."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from app.visualizations.analytics_view import analytics_dashboard_data
from app.visualizations.governance_view import governance_dashboard_data
from app.visualizations.graph_explorer import graph_explorer_data
from app.visualizations.ontology_browser import ontology_browser_data
from app.visualizations.provenance_view import provenance_view_data
from app.visualizations.reasoning_view import explanations_data, reasoning_dashboard_data
from semantic_platform.search import search_graph

visualization_bp = Blueprint("visualization", __name__)


@visualization_bp.get("/graph")
def graph_explorer():
    """Render interactive knowledge graph exploration."""
    return render_template(
        "graph_explorer.html",
        graph=graph_explorer_data(node=request.args.get("node"), query=request.args.get("q")),
        query=request.args.get("q", ""),
    )


@visualization_bp.get("/ontology-browser")
def ontology_browser():
    """Render ontology hierarchy, property, and instance browser."""
    return render_template("ontology_browser.html", data=ontology_browser_data())


@visualization_bp.get("/governance-dashboard")
def governance_dashboard():
    """Render governance oversight dashboard."""
    return render_template("governance_dashboard.html", data=governance_dashboard_data())


@visualization_bp.get("/provenance-explorer")
def provenance_explorer():
    """Render provenance lineage explorer."""
    return render_template("provenance_explorer.html", data=provenance_view_data())


@visualization_bp.get("/reasoning-dashboard")
def reasoning_dashboard():
    """Render reasoning explainability dashboard."""
    return render_template("reasoning_dashboard.html", data=reasoning_dashboard_data())


@visualization_bp.get("/explanations")
def explanations():
    """Render detailed inference explanations."""
    return render_template("explanation_explorer.html", rows=explanations_data())


@visualization_bp.get("/analytics")
def analytics():
    """Render graph analytics dashboard."""
    return render_template("analytics.html", metrics=analytics_dashboard_data())


@visualization_bp.route("/search", methods=["GET", "POST"])
def search():
    """Render semantic search over platform assets."""
    query = request.values.get("q", "")
    results = search_graph(query) if query else []
    return render_template("search.html", query=query, results=results)
