"""SPARQL query routes."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from semantic_platform.config import load_settings
from semantic_platform.query import read_query
from semantic_platform.api import run_local_query

query_bp = Blueprint("query", __name__, url_prefix="/query")


@query_bp.route("", methods=["GET", "POST"])
def index():
    """Render and execute a simple local SPARQL form."""
    settings = load_settings()
    query_text = read_query(settings.default_query_file)
    rows = None
    error = None
    if request.method == "POST":
        query_text = request.form.get("query", query_text)
        try:
            rows = run_local_query(query_text, settings=settings)
        except Exception as exc:  # Query authoring errors should be shown in the MVP UI.
            error = str(exc)
    return render_template("query.html", query=query_text, rows=rows, error=error)
