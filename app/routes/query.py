"""query route skeleton."""

from flask import Blueprint, jsonify

query_bp = Blueprint("query", __name__, url_prefix="/query")


@query_bp.get("")
def index():
    """Return a placeholder response until query UI/API behavior is implemented."""
    return jsonify({"status": "not_implemented", "component": "query"}), 501
