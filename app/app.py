"""Flask application factory skeleton."""

from flask import Flask

from app.routes.graph import graph_bp
from app.routes.governance import governance_bp
from app.routes.health import health_bp
from app.routes.mappings import mappings_bp
from app.routes.ontology import ontology_bp
from app.routes.provenance import provenance_bp
from app.routes.query import query_bp


def create_app() -> Flask:
    """Create the Flask app and register route blueprints."""
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(ontology_bp)
    app.register_blueprint(governance_bp)
    app.register_blueprint(provenance_bp)
    app.register_blueprint(mappings_bp)
    app.register_blueprint(query_bp)
    return app
