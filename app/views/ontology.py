"""Ontology views: raw ontology text and the interactive ontology browser."""

from __future__ import annotations

from flask import g, render_template

from app.visualizations.ontology_browser import ontology_browser_data
from semantic_platform.api import get_ontology_text


def text(scope=None):
    """Render the concatenated ontology Turtle for the active context."""
    scope = scope or g.scope
    return render_template("ontology.html", ontology=get_ontology_text(settings=scope.settings))


def browser(scope=None):
    """Render the ontology hierarchy, property, and instance browser."""
    scope = scope or g.scope
    return render_template("ontology_browser.html", data=ontology_browser_data(settings=scope.settings))
