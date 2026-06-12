"""Provenance UI route (System tree). Logic lives in :mod:`app.views.provenance`."""

from __future__ import annotations

from flask import Blueprint

from app.views import provenance as provenance_view

provenance_bp = Blueprint("provenance", __name__, url_prefix="/provenance")


@provenance_bp.get("")
def index():
    """Render provenance activity summary."""
    return provenance_view.summary()
