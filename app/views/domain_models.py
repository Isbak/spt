"""Domain model bundles and discovered SHACL shapes for the active context."""

from __future__ import annotations

from flask import g, render_template

from semantic_platform.api import get_domain_models, list_shape_records


def domain_models(scope=None):
    """Render domain models grouped from ontology, shapes, and mappings."""
    scope = scope or g.scope
    return render_template("domain_models.html", domains=get_domain_models(settings=scope.settings))


def shapes(scope=None):
    """Render discovered SHACL shapes."""
    scope = scope or g.scope
    return render_template("shapes.html", shapes=list_shape_records(settings=scope.settings))
