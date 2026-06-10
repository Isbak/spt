"""Provenance UI route."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.config import load_settings
from semantic_platform.provenance import load_provenance_graph
from semantic_platform.query import read_query, result_rows

provenance_bp = Blueprint("provenance", __name__, url_prefix="/provenance")


def provenance_summary() -> list[dict[str, str]]:
    """Return provenance trace rows using the service/query layer."""
    settings = load_settings()
    graph = load_provenance_graph(settings=settings)
    result = graph.query(read_query(settings.queries_dir / "provenance_trace.rq"))
    return result_rows(result)


@provenance_bp.get("")
def index():
    """Render provenance activity summary."""
    return render_template("provenance.html", rows=provenance_summary())
