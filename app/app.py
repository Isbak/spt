"""Flask application factory for the Semantic Platform UI."""

from __future__ import annotations

from flask import Flask, render_template

from app.routes.graph import graph_bp
from app.routes.health import health_bp
from app.routes.governance import governance_bp
from app.routes.named_graphs import named_graphs_bp
from app.routes.ontology_version import ontology_version_bp
from app.routes.provenance import provenance_bp
from app.routes.ontology import ontology_bp
from app.routes.query import query_bp
from app.routes.reasoning import reasoning_bp
from app.routes.mappings import integration_bp, mapping_lineage_bp, mappings_bp, source_catalog_bp


def create_app() -> Flask:
    """Create the Flask app and register Phase 1 route blueprints."""
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(ontology_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(governance_bp)
    app.register_blueprint(provenance_bp)
    app.register_blueprint(named_graphs_bp)
    app.register_blueprint(ontology_version_bp)
    app.register_blueprint(mappings_bp)
    app.register_blueprint(source_catalog_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(mapping_lineage_bp)
    app.register_blueprint(reasoning_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
