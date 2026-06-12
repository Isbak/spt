"""Graph routes (System tree). Logic lives in :mod:`app.views.graph`."""

from __future__ import annotations

from flask import Blueprint

from app.views import graph as graph_view

graph_bp = Blueprint("graph", __name__)


@graph_bp.get("/graphs")
def index():
    """Render local RDF graph statistics."""
    return graph_view.stats()
