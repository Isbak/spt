"""Ontology version metadata view for the active context."""

from __future__ import annotations

from flask import g, render_template

from semantic_platform.ontology_version import ontology_version_summary


def index(scope=None):
    """Render the ontology version metadata summary."""
    scope = scope or g.scope
    return render_template("ontology_version.html", summary=ontology_version_summary(settings=scope.settings))
