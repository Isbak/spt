"""Flask application factory for the Semantic Platform UI."""

from __future__ import annotations

from flask import Flask, render_template

from app.routes.graph import graph_bp
from app.routes.health import health_bp
from app.routes.ontology import ontology_bp
from app.routes.query import query_bp


def create_app() -> Flask:
    """Create the Flask app and register Phase 1 route blueprints."""
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(ontology_bp)
    app.register_blueprint(query_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
