"""Graph views: local RDF statistics and the interactive graph explorer."""

from __future__ import annotations

from flask import g, jsonify, render_template, request

from app.visualizations.graph_explorer import graph_explorer_data
from semantic_platform.api import get_graph_stats
from semantic_platform.graph import load_graph
from semantic_platform.graph_view import node_detail


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


def node(scope=None):
    """Return JSON detail for a single graph node (the right-hand sidebar payload).

    Degrades to a 200 with an ``error`` note when ``uri`` is absent, matching the
    platform's "every GET route returns 200" contract.
    """
    scope = scope or g.scope
    uri = request.args.get("uri", "")
    if not uri:
        return jsonify({"id": "", "error": "uri is required."})
    return jsonify(node_detail(load_graph(settings=scope.settings), uri))
