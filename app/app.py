"""Flask application factory for the Semantic Platform UI."""

from __future__ import annotations

from flask import Flask, render_template, request

from app.page_context import resolve_page_context
from app.routes.advisory import advisory_bp
from app.routes.agents import agents_bp
from app.routes.chat import chat_bp
from app.routes.graph import graph_bp
from app.routes.health import health_bp
from app.routes.governance import governance_bp
from app.routes.fabric import fabric_bp
from app.routes.execution import execution_bp
from app.routes.domain_models import domain_models_bp, shapes_bp
from app.routes.named_graphs import named_graphs_bp
from app.routes.ontology_version import ontology_version_bp
from app.routes.orchestration import orchestration_bp
from app.routes.multi_agent import multi_agent_bp
from app.routes.provenance import provenance_bp
from app.routes.ontology import ontology_bp
from app.routes.query import query_bp
from app.routes.reasoning import reasoning_bp
from app.routes.setup import setup_bp
from app.routes.studio import studio_bp
from app.routes.visualization import visualization_bp
from app.routes.materialization import materialization_bp
from app.routes.mappings import integration_bp, mapping_lineage_bp, mappings_bp, source_catalog_bp


def create_app() -> Flask:
    """Create the Flask app and register Phase 1 route blueprints."""
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(ontology_bp)
    app.register_blueprint(shapes_bp)
    app.register_blueprint(domain_models_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(governance_bp)
    app.register_blueprint(provenance_bp)
    app.register_blueprint(named_graphs_bp)
    app.register_blueprint(ontology_version_bp)
    app.register_blueprint(mappings_bp)
    app.register_blueprint(source_catalog_bp)
    app.register_blueprint(integration_bp)
    app.register_blueprint(mapping_lineage_bp)
    app.register_blueprint(materialization_bp)
    app.register_blueprint(reasoning_bp)
    app.register_blueprint(visualization_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(advisory_bp)
    app.register_blueprint(orchestration_bp)
    app.register_blueprint(execution_bp)
    app.register_blueprint(multi_agent_bp)
    app.register_blueprint(fabric_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(studio_bp)

    @app.context_processor
    def inject_page_context():
        """Expose the current view's chat scope to every template."""
        return {"page_context": resolve_page_context(request.endpoint)}

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
