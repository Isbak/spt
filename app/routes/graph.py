"""Graph routes."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.api import get_graph_stats

graph_bp = Blueprint("graph", __name__)


@graph_bp.get("/graphs")
def index():
    """Render local RDF graph statistics."""
    return render_template("graphs.html", stats=get_graph_stats())
