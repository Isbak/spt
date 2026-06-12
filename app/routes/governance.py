"""Governance UI route (System tree)."""

from __future__ import annotations

from flask import Blueprint

from app.views import governance as governance_view

governance_bp = Blueprint("governance", __name__, url_prefix="/governance")


@governance_bp.get("")
def index():
    """Render governance metadata summary."""
    return governance_view.summary()
