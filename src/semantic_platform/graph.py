"""RDF graph loading and statistics utilities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import logging
from pathlib import Path

from rdflib import Graph

from semantic_platform.config import Settings, load_settings

LOGGER = logging.getLogger(__name__)
RDF_EXTENSIONS = {".ttl": "turtle", ".rdf": "xml", ".xml": "xml", ".nt": "nt", ".n3": "n3"}


@dataclass(frozen=True)
class GraphStats:
    """Simple graph statistics for display and tests."""

    triples: int
    subjects: int
    predicates: int
    objects: int


def rdf_files(paths: Iterable[Path]) -> list[Path]:
    """Return sorted RDF files from a sequence of files or directories."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.suffix.lower() in RDF_EXTENSIONS)
        elif path.is_file() and path.suffix.lower() in RDF_EXTENSIONS:
            files.append(path)
    return sorted(set(files))


def parse_file(graph: Graph, path: Path) -> None:
    """Parse one RDF file into ``graph`` using an extension-based format."""
    rdf_format = RDF_EXTENSIONS.get(path.suffix.lower())
    if not rdf_format:
        raise ValueError(f"Unsupported RDF file extension: {path}")
    LOGGER.info("Parsing RDF file %s as %s", path, rdf_format)
    graph.parse(path, format=rdf_format)


def load_graph(paths: Iterable[Path] | None = None, settings: Settings | None = None) -> Graph:
    """Load RDF from supplied paths or configured local RDF asset directories."""
    settings = settings or load_settings()
    selected_paths = list(paths) if paths is not None else [
        settings.ontology_dir,
        settings.vocabularies_dir,
        settings.data_dir,
        settings.graphs_dir,
    ]
    graph = Graph()
    for path in rdf_files(selected_paths):
        parse_file(graph, path)
    LOGGER.info("Loaded %s triples", len(graph))
    return graph


def graph_stats(graph: Graph) -> GraphStats:
    """Calculate basic RDF graph statistics."""
    return GraphStats(
        triples=len(graph),
        subjects=len(set(graph.subjects())),
        predicates=len(set(graph.predicates())),
        objects=len(set(graph.objects())),
    )
