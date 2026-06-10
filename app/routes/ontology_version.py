"""Ontology version UI route."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.ontology_version import ontology_version_summary

ontology_version_bp = Blueprint("ontology_version", __name__, url_prefix="/ontology-version")


@ontology_version_bp.get("")
def index():
    """Render ontology version metadata summary."""
    return render_template("ontology_version.html", summary=ontology_version_summary())
