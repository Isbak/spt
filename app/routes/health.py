"""Health routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from semantic_platform.api import fuseki_health

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """Return application and Fuseki health."""
    fuseki = fuseki_health()
    payload = {
        "status": "ok",
        "fuseki": {
            "ok": fuseki.ok,
            "status_code": fuseki.status_code,
            "message": fuseki.message,
        },
    }
    return jsonify(payload)


@health_bp.get("/health/view")
def health_view():
    """Render a simple health page."""
    return render_template("health.html", fuseki=fuseki_health())
