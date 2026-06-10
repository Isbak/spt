"""Governance UI route."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.governance import governance_summary

governance_bp = Blueprint("governance", __name__, url_prefix="/governance")


@governance_bp.get("")
def index():
    """Render governance metadata summary."""
    return render_template("governance.html", summary=governance_summary())
