"""Named graph manifest UI route."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.named_graphs import graph_lifecycle_summary

named_graphs_bp = Blueprint("named_graphs", __name__, url_prefix="/named-graphs")


@named_graphs_bp.get("")
def index():
    """Render named graph lifecycle summary."""
    return render_template("named_graphs.html", summary=graph_lifecycle_summary())
