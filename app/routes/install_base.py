"""Install-base materialization UI route.

Surfaces drop-in R2RML materialization: it runs every mapping against the
configured relational source and shows the resulting record/triple counts and
target named graphs, plus whether Fuseki is reachable for serving them.
"""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.api import fuseki_health, materialize_sources

install_base_bp = Blueprint("install_base", __name__, url_prefix="/install-base")


@install_base_bp.get("")
def install_base_index():
    """Materialize configured mappings and render the results."""
    results = materialize_sources()
    return render_template(
        "install_base.html",
        results=results,
        fuseki=fuseki_health(),
    )
