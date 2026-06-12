"""Graph views: local RDF statistics and the interactive graph explorer."""

from __future__ import annotations

from flask import g, render_template, request

from app.visualizations.graph_explorer import graph_explorer_data
from semantic_platform.api import get_graph_stats


def stats(scope=None):
    """Render local RDF graph statistics for the active context."""
    scope = scope or g.scope
    return render_template("graphs.html", stats=get_graph_stats(settings=scope.settings))


def explorer(scope=None):
    """Render interactive knowledge graph exploration for the active context."""
    scope = scope or g.scope
    return render_template(
        "graph_explorer.html",
        graph=graph_explorer_data(
            node=request.args.get("node"),
            query=request.args.get("q"),
            settings=scope.settings,
        ),
        query=request.args.get("q", ""),
    )
