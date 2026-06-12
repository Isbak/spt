"""Ontology version UI route (System tree)."""

from __future__ import annotations

from flask import Blueprint

from app.views import ontology_version as ontology_version_view

ontology_version_bp = Blueprint("ontology_version", __name__, url_prefix="/ontology-version")


@ontology_version_bp.get("")
def index():
    """Render ontology version metadata summary."""
    return ontology_version_view.index()
