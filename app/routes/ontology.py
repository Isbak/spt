"""Ontology routes."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.api import get_ontology_text

ontology_bp = Blueprint("ontology", __name__, url_prefix="/ontology")


@ontology_bp.get("")
def index():
    """Render the core ontology text."""
    return render_template("ontology.html", ontology=get_ontology_text())
