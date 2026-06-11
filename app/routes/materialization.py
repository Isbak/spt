"""Source materialization UI route.

Surfaces drop-in R2RML materialization: it runs every mapping in
``mappings/r2rml/`` against the configured relational source and shows the
resulting record/triple counts and target named graphs, plus whether Fuseki is
reachable for serving them.
"""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.api import (
    fuseki_graph_triple_counts,
    fuseki_health,
    materialize_sources,
)

materialization_bp = Blueprint("materialization", __name__, url_prefix="/materialization")


@materialization_bp.get("")
def materialization_index():
    """Materialize configured mappings and render the results.

    When Apache Jena/Fuseki is available, also read back the live triple count
    per target graph so the page confirms the data is served, not just
    materialized locally.
    """
    results = materialize_sources()
    fuseki = fuseki_health()
    counts = fuseki_graph_triple_counts([result.target_graph for result in results]) if fuseki.ok else {}
    return render_template(
        "materialization.html",
        results=results,
        fuseki=fuseki,
        fuseki_counts=counts,
    )
