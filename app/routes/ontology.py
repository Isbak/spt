"""Ontology routes (System tree). Logic lives in :mod:`app.views.ontology`."""

from __future__ import annotations

from flask import Blueprint

from app.views import ontology as ontology_view

ontology_bp = Blueprint("ontology", __name__, url_prefix="/ontology")


@ontology_bp.get("")
def index():
    """Render the core ontology text for the active (System) context."""
    return ontology_view.text()
