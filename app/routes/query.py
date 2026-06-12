"""SPARQL query routes (System tree). Logic lives in :mod:`app.views.query`."""

from __future__ import annotations

from flask import Blueprint

from app.views import query as query_view

query_bp = Blueprint("query", __name__, url_prefix="/query")


@query_bp.route("", methods=["GET", "POST"])
def index():
    """Render and execute a simple local SPARQL form."""
    return query_view.index()
