"""SPARQL query and semantic search views for the active context."""

from __future__ import annotations

from flask import g, render_template, request

from semantic_platform.api import run_local_query
from semantic_platform.query import read_query
from semantic_platform.search import search_graph


def _default_query(settings) -> str:
    """Return the context's default query text, or empty when none is present."""
    path = settings.default_query_file
    return read_query(path) if path.is_file() else ""


def index(scope=None):
    """Render and execute a simple local SPARQL form over the active context."""
    scope = scope or g.scope
    settings = scope.settings
    query_text = _default_query(settings)
    rows = None
    error = None
    if request.method == "POST":
        query_text = request.form.get("query", query_text)
        try:
            rows = run_local_query(query_text, settings=settings)
        except Exception as exc:  # Query authoring errors should be shown in the MVP UI.
            error = str(exc)
    return render_template("query.html", query=query_text, rows=rows, error=error)


def search(scope=None):
    """Render semantic search over the active context's assets."""
    scope = scope or g.scope
    query = request.values.get("q", "")
    results = search_graph(query, settings=scope.settings) if query else []
    return render_template("search.html", query=query, results=results)
