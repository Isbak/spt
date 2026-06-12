"""Reasoning UI routes (System tree). Logic lives in :mod:`app.views.reasoning`."""

from __future__ import annotations

from flask import Blueprint

from app.views import reasoning as reasoning_view

reasoning_bp = Blueprint("reasoning", __name__)


@reasoning_bp.get("/reasoning")
def reasoning_index():
    """Render reasoning engine status and statistics."""
    return reasoning_view.index()


@reasoning_bp.get("/inferences")
def inferences_index():
    """Render inferred assertions."""
    return reasoning_view.inferences()


@reasoning_bp.get("/legacy-explanations")
def explanations_index():
    """Render generated inference explanations."""
    return reasoning_view.legacy_explanations()


@reasoning_bp.get("/consistency")
def consistency_index():
    """Render semantic consistency report."""
    return reasoning_view.consistency()


@reasoning_bp.get("/rules")
def rules_index():
    """Render governed reasoning rules."""
    return reasoning_view.rules()
