"""Governance views: metadata summary and the oversight dashboard."""

from __future__ import annotations

from flask import g, render_template

from app.visualizations.governance_view import governance_dashboard_data
from semantic_platform.governance import governance_summary


def summary(scope=None):
    """Render the governance metadata summary for the active context."""
    scope = scope or g.scope
    return render_template("governance.html", summary=governance_summary(settings=scope.settings))


def dashboard(scope=None):
    """Render the governance oversight dashboard for the active context."""
    scope = scope or g.scope
    return render_template("governance_dashboard.html", data=governance_dashboard_data(settings=scope.settings))
