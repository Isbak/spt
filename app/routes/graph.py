"""graph route skeleton."""

from flask import Blueprint, jsonify

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")


@graph_bp.get("")
def index():
    """Return a placeholder response until graph UI/API behavior is implemented."""
    return jsonify({"status": "not_implemented", "component": "graph"}), 501
