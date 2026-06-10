"""Health route skeleton."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """Return a minimal health response for container smoke tests."""
    return jsonify({"status": "ok"})
