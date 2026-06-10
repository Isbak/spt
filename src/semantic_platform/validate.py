"""RDF syntax and SHACL validation services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from pyshacl import validate as pyshacl_validate
from rdflib import Graph

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph, parse_file, rdf_files

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyntaxValidationResult:
    """Result for one RDF syntax validation check."""

    path: Path
    valid: bool
    message: str = ""


@dataclass(frozen=True)
class ShaclValidationReport:
    """SHACL validation result and report text."""

    conforms: bool
    report_graph: Graph
    report_text: str


def validate_rdf_syntax(paths: list[Path] | None = None, settings: Settings | None = None) -> list[SyntaxValidationResult]:
    """Parse RDF files individually and report syntax errors without masking file names."""
    settings = settings or load_settings()
    selected_paths = paths or [settings.ontology_dir, settings.vocabularies_dir, settings.data_dir, settings.shapes_dir]
    results: list[SyntaxValidationResult] = []
    for path in rdf_files(selected_paths):
        graph = Graph()
        try:
            parse_file(graph, path)
        except Exception as exc:  # pragma: no cover - exact parser exceptions vary by format
            LOGGER.exception("RDF syntax validation failed for %s", path)
            results.append(SyntaxValidationResult(path=path, valid=False, message=str(exc)))
        else:
            results.append(SyntaxValidationResult(path=path, valid=True))
    return results


def validate_shacl(data_graph: Graph | None = None, settings: Settings | None = None) -> ShaclValidationReport:
    """Validate configured RDF assets against configured SHACL shapes."""
    settings = settings or load_settings()
    data_graph = data_graph or load_graph(settings=settings)
    shapes_graph = load_graph([settings.shapes_dir], settings=settings)
    conforms, report_graph, report_text = pyshacl_validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=False,
        js=False,
    )
    LOGGER.info("SHACL validation conforms=%s", conforms)
    return ShaclValidationReport(bool(conforms), report_graph, str(report_text))


def run_validation(settings: Settings | None = None) -> tuple[list[SyntaxValidationResult], ShaclValidationReport]:
    """Run RDF syntax validation and SHACL validation."""
    settings = settings or load_settings()
    syntax_results = validate_rdf_syntax(settings=settings)
    shacl_report = validate_shacl(settings=settings)
    return syntax_results, shacl_report
