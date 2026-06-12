"""Provenance views: activity trace summary and the lineage explorer."""

from __future__ import annotations

from flask import g, render_template

from app.visualizations.provenance_view import provenance_view_data
from semantic_platform.config import Settings
from semantic_platform.provenance import load_provenance_graph
from semantic_platform.query import read_query, result_rows


def provenance_rows(settings: Settings) -> list[dict[str, str]]:
    """Return provenance trace rows via the service/query layer.

    Degrades to an empty list when the context has no ``provenance_trace.rq`` query
    (e.g. a freshly-scaffolded domain), keeping the GET route at 200.
    """
    query_path = settings.queries_dir / "provenance_trace.rq"
    if not query_path.is_file():
        return []
    graph = load_provenance_graph(settings=settings)
    result = graph.query(read_query(query_path))
    return result_rows(result)


def summary(scope=None):
    """Render the provenance activity summary for the active context."""
    scope = scope or g.scope
    return render_template("provenance.html", rows=provenance_rows(scope.settings))


def explorer(scope=None):
    """Render the PROV-O lineage explorer for the active context."""
    scope = scope or g.scope
    return render_template("provenance_explorer.html", data=provenance_view_data(settings=scope.settings))
