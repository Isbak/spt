"""Domain model and SHACL shape UI routes.

The ``domain_models`` blueprint surfaces drop-in / uploaded domain bundles
grouped by namespace and accepts new bundles through an upload form. The
``shapes`` blueprint renders the discovered SHACL shapes. Both read fresh from
the RDF tree on every request, so a successful upload (or a file dropped on
disk) is visible immediately.
"""

from __future__ import annotations

from flask import Blueprint, render_template, request

from semantic_platform.api import get_domain_models, import_domain, list_shape_records

domain_models_bp = Blueprint("domain_models", __name__, url_prefix="/domain-models")
shapes_bp = Blueprint("shapes", __name__, url_prefix="/shapes")

_UPLOAD_FIELDS = ("ontology", "shape", "mapping")


@domain_models_bp.get("")
def index():
    """Render domain models grouped from ontology, shapes, and mappings."""
    return render_template("domain_models.html", domains=get_domain_models())


@domain_models_bp.post("/import")
def import_view():
    """Validate and write an uploaded domain bundle, then re-render the page."""
    files: dict[str, tuple[str, bytes]] = {}
    for field in _UPLOAD_FIELDS:
        uploaded = request.files.get(field)
        if uploaded and uploaded.filename:
            files[field] = (uploaded.filename, uploaded.read())
    result = import_domain(**files)
    return render_template("domain_models.html", domains=get_domain_models(), result=result)


@shapes_bp.get("")
def index():  # noqa: F811 - blueprint-scoped endpoint, distinct from domain_models.index
    """Render discovered SHACL shapes."""
    return render_template("shapes.html", shapes=list_shape_records())
