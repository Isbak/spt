"""mappings route skeleton."""

from flask import Blueprint, jsonify

mappings_bp = Blueprint("mappings", __name__, url_prefix="/mappings")


@mappings_bp.get("")
def index():
    """Return a placeholder response until mappings UI/API behavior is implemented."""
    return jsonify({"status": "not_implemented", "component": "mappings"}), 501
