"""governance route skeleton."""

from flask import Blueprint, jsonify

governance_bp = Blueprint("governance", __name__, url_prefix="/governance")


@governance_bp.get("")
def index():
    """Return a placeholder response until governance UI/API behavior is implemented."""
    return jsonify({"status": "not_implemented", "component": "governance"}), 501
