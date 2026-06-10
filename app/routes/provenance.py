"""provenance route skeleton."""

from flask import Blueprint, jsonify

provenance_bp = Blueprint("provenance", __name__, url_prefix="/provenance")


@provenance_bp.get("")
def index():
    """Return a placeholder response until provenance UI/API behavior is implemented."""
    return jsonify({"status": "not_implemented", "component": "provenance"}), 501
