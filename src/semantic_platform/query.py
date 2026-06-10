"""SPARQL query execution utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

from rdflib import Graph
from rdflib.query import Result

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

LOGGER = logging.getLogger(__name__)


def read_query(path: Path) -> str:
    """Read a SPARQL query file."""
    LOGGER.info("Reading SPARQL query %s", path)
    return path.read_text(encoding="utf-8")


def execute_query(query_text: str, graph: Graph | None = None) -> Result:
    """Execute SPARQL against an in-memory RDFLib graph."""
    graph = graph or load_graph()
    LOGGER.info("Executing local SPARQL query")
    return graph.query(query_text)


def result_rows(result: Result) -> list[dict[str, Any]]:
    """Convert SELECT query results to dictionaries with string values."""
    rows: list[dict[str, Any]] = []
    for row in result:
        rows.append({str(var): str(row[var]) for var in result.vars if row[var] is not None})
    return rows


def execute_default_query(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Execute the configured validation query against local RDF assets."""
    settings = settings or load_settings()
    graph = load_graph(settings=settings)
    result = execute_query(read_query(settings.default_query_file), graph)
    return result_rows(result)
