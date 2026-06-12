"""Named graph manifest UI route (System tree)."""

from __future__ import annotations

from flask import Blueprint

from app.views import named_graphs as named_graphs_view

named_graphs_bp = Blueprint("named_graphs", __name__, url_prefix="/named-graphs")


@named_graphs_bp.get("")
def index():
    """Render named graph lifecycle summary."""
    return named_graphs_view.index()
