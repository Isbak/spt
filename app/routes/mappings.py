"""Semantic integration UI routes."""

from __future__ import annotations

from flask import Blueprint, render_template

from semantic_platform.config import load_settings
from semantic_platform.graph import load_graph
from semantic_platform.mappings import list_mappings
from semantic_platform.query import read_query, result_rows
from semantic_platform.source_catalog import list_source_datasets

mappings_bp = Blueprint("mappings", __name__, url_prefix="/mappings")
source_catalog_bp = Blueprint("source_catalog", __name__, url_prefix="/source-catalog")
integration_bp = Blueprint("integration", __name__, url_prefix="/integration")
mapping_lineage_bp = Blueprint("mapping_lineage", __name__, url_prefix="/mapping-lineage")


@mappings_bp.get("")
def index():
    """Render discovered mappings and lifecycle metadata."""
    return render_template("mappings.html", mappings=list_mappings())


@source_catalog_bp.get("")
def source_catalog_index():
    """Render registered source systems and datasets."""
    return render_template("source_catalog.html", datasets=list_source_datasets())


@integration_bp.get("")
def integration_index():
    """Render integration named graph assignments."""
    rows = _query_rows("integration_graphs.rq")
    return render_template("integration.html", rows=rows)


@mapping_lineage_bp.get("")
def mapping_lineage_index():
    """Render source-to-RDF mapping provenance lineage."""
    rows = _query_rows("mapping_lineage.rq")
    return render_template("mapping_lineage.html", rows=rows)


def _query_rows(query_name: str) -> list[dict[str, str]]:
    settings = load_settings()
    graph = load_graph(settings=settings)
    return result_rows(graph.query(read_query(settings.queries_dir / query_name)))
