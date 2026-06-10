"""ontology route skeleton."""

from flask import Blueprint, jsonify

ontology_bp = Blueprint("ontology", __name__, url_prefix="/ontology")


@ontology_bp.get("")
def index():
    """Return a placeholder response until ontology UI/API behavior is implemented."""
    return jsonify({"status": "not_implemented", "component": "ontology"}), 501
