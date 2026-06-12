"""Domain model and SHACL shape UI routes (System tree).

The ``domain_models`` blueprint surfaces domain bundles grouped by namespace — a
read-only view assembled fresh from the RDF tree on every request, so a file dropped on
disk (or authored through the Studio) is visible immediately. The ``shapes`` blueprint
renders the discovered SHACL shapes. Authoring new domain content is handled by the
governed Studio flow (ADR-0016), not an upload form. View logic lives in
:mod:`app.views.domain_models`.
"""

from __future__ import annotations

from flask import Blueprint

from app.views import domain_models as domain_models_view

domain_models_bp = Blueprint("domain_models", __name__, url_prefix="/domain-models")
shapes_bp = Blueprint("shapes", __name__, url_prefix="/shapes")


@domain_models_bp.get("")
def index():
    """Render domain models grouped from ontology, shapes, and mappings."""
    return domain_models_view.domain_models()


@shapes_bp.get("")
def index():  # noqa: F811 - blueprint-scoped endpoint, distinct from domain_models.index
    """Render discovered SHACL shapes."""
    return domain_models_view.shapes()
