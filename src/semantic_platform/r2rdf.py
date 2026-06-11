"""R2RDF and R2RML utilities for semantic source integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from string import Formatter
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCTERMS, PROV, RDFS, XSD

from semantic_platform.config import Settings, load_settings

RR = Namespace("http://www.w3.org/ns/r2rml#")
SP = Namespace("https://example.org/semantic-platform/core#")
MAP = Namespace("https://example.org/semantic-platform/mappings#")
GOV = Namespace("https://example.org/semantic-platform/governance#")
RESOURCE = Namespace("https://example.org/resource/")


@dataclass(frozen=True)
class MappingValidationResult:
    """Validation result for one mapping graph."""

    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MappingExecutionResult:
    """Result of executing a lightweight mapping workflow."""

    graph: Graph
    execution_iri: URIRef
    triple_count: int


MAPPING_EXTENSIONS = (".ttl", ".r2rml")


def load_r2rml_mapping(path: Path | str) -> Graph:
    """Load an R2RML mapping file (``.ttl`` or ``.r2rml``) into an RDF graph.

    Both extensions are parsed as Turtle; ``.r2rml`` is accepted so that
    drop-in mapping files do not need to be renamed.
    """
    graph = Graph()
    graph.parse(Path(path), format="turtle")
    return graph


def mapping_files(settings: Settings | None = None) -> list[Path]:
    """Return available R2RML mapping files (``.ttl`` and ``.r2rml``)."""
    settings = settings or load_settings()
    root = settings.r2rml_dir
    paths: list[Path] = []
    for extension in MAPPING_EXTENSIONS:
        paths.extend(root.glob(f"*{extension}"))
    return sorted(paths)


def quote_table_name(table_name: str) -> str:
    """Delimit an ``rr:tableName`` value into a valid SQL table reference.

    A bare ``rr:tableName`` is interpolated straight into ``SELECT * FROM ...``,
    so any name that is not a simple unquoted identifier — a schema-qualified
    name (``app.person``), or a name containing spaces, hyphens, or a reserved
    word — produces a SQL syntax error (e.g. ``near ".": syntax error``). Per the
    SQL standard each dot-separated component is wrapped in double quotes (with
    embedded quotes doubled) so these names round-trip safely. Values the mapping
    author has already delimited (a leading ``"``, ``[``, or backtick) or
    expressed as a sub-select (a leading ``(``) are passed through unchanged.
    """
    stripped = table_name.strip()
    if not stripped or stripped[0] in "\"[(`":
        return stripped
    return ".".join('"' + part.replace('"', '""') + '"' for part in stripped.split("."))


def logical_table_sql(mapping_graph: Graph, triples_map: URIRef) -> str:
    """Return the SQL query for a mapping's ``rr:logicalTable``.

    Supports both ``rr:sqlQuery`` (verbatim) and ``rr:tableName`` (expanded to
    ``SELECT * FROM <table>``, with the table name delimited via
    :func:`quote_table_name`). Raises ``ValueError`` when neither is present.
    """
    logical_table = next(mapping_graph.objects(triples_map, RR.logicalTable), None)
    if logical_table is None:
        raise ValueError(f"{triples_map} is missing rr:logicalTable.")
    sql_query = next(mapping_graph.objects(logical_table, RR.sqlQuery), None)
    if sql_query is not None:
        return str(sql_query)
    table_name = next(mapping_graph.objects(logical_table, RR.tableName), None)
    if table_name is not None:
        return f"SELECT * FROM {quote_table_name(str(table_name))}"
    raise ValueError(f"{triples_map} rr:logicalTable needs rr:sqlQuery or rr:tableName.")


def validate_mapping(graph: Graph) -> MappingValidationResult:
    """Validate required R2RML and Semantic Platform mapping metadata."""
    errors: list[str] = []
    triples_maps = set(graph.subjects(RDF.type, RR.TriplesMap)) | set(graph.subjects(RDF.type, MAP.Mapping))
    if not triples_maps:
        errors.append("Mapping graph must contain at least one rr:TriplesMap or map:Mapping.")
    for triples_map in triples_maps:
        if (triples_map, RR.subjectMap, None) not in graph:
            errors.append(f"{triples_map} is missing rr:subjectMap.")
        if (triples_map, RR.predicateObjectMap, None) not in graph:
            errors.append(f"{triples_map} is missing rr:predicateObjectMap.")
        if (triples_map, MAP.sourcedFrom, None) not in graph:
            errors.append(f"{triples_map} is missing map:sourcedFrom.")
        if (triples_map, MAP.targetGraph, None) not in graph:
            errors.append(f"{triples_map} is missing map:targetGraph.")
        if (triples_map, MAP.version, None) not in graph:
            errors.append(f"{triples_map} is missing map:version.")
        if (triples_map, GOV.hasOwner, None) not in graph:
            errors.append(f"{triples_map} is missing gov:hasOwner.")
        if (triples_map, GOV.hasSteward, None) not in graph:
            errors.append(f"{triples_map} is missing gov:hasSteward.")
    return MappingValidationResult(valid=not errors, errors=errors)


def validate_mapping_file(path: Path | str) -> MappingValidationResult:
    """Load and validate a mapping file."""
    return validate_mapping(load_r2rml_mapping(path))


def _format_template(template: str, row: dict[str, Any]) -> str:
    values = {key: "" if value is None else str(value) for key, value in row.items()}
    for _, field_name, _, _ in Formatter().parse(template):
        if field_name and field_name not in values:
            values[field_name] = ""
    return template.format(**values)


def _subject_for_map(mapping_graph: Graph, triples_map: URIRef, row: dict[str, Any]) -> URIRef:
    subject_map = next(mapping_graph.objects(triples_map, RR.subjectMap))
    template = next(mapping_graph.objects(subject_map, RR.template), None)
    constant = next(mapping_graph.objects(subject_map, RR.constant), None)
    if template is not None:
        return URIRef(_format_template(str(template), row))
    if constant is not None:
        return URIRef(str(constant))
    raise ValueError(f"{triples_map} subject map must define rr:template or rr:constant")


def generate_rdf_from_rows(
    mapping_graph: Graph,
    rows: list[dict[str, Any]],
    *,
    source_dataset: URIRef | None = None,
) -> Graph:
    """Generate RDF from rows using a practical subset of R2RML patterns."""
    output = Graph()
    output.bind("sp", SP)
    output.bind("map", MAP)
    output.bind("prov", PROV)
    output.bind("dcterms", DCTERMS)
    for triples_map in set(mapping_graph.subjects(RDF.type, RR.TriplesMap)):
        subject_map = next(mapping_graph.objects(triples_map, RR.subjectMap))
        classes = list(mapping_graph.objects(subject_map, RR["class"]))
        for row in rows:
            subject = _subject_for_map(mapping_graph, triples_map, row)
            for mapped_class in classes:
                output.add((subject, RDF.type, mapped_class))
            if source_dataset is not None:
                output.add((subject, SP.belongsToDataset, source_dataset))
            for pom in mapping_graph.objects(triples_map, RR.predicateObjectMap):
                predicate = next(mapping_graph.objects(pom, RR.predicate), None)
                object_map = next(mapping_graph.objects(pom, RR.objectMap), None)
                if predicate is None or object_map is None:
                    continue
                obj = _object_from_map(mapping_graph, object_map, row)
                if obj is not None:
                    output.add((subject, predicate, obj))
    return output


def _object_from_map(mapping_graph: Graph, object_map: URIRef, row: dict[str, Any]) -> URIRef | Literal | None:
    constant = next(mapping_graph.objects(object_map, RR.constant), None)
    template = next(mapping_graph.objects(object_map, RR.template), None)
    column = next(mapping_graph.objects(object_map, RR.column), None)
    term_type = next(mapping_graph.objects(object_map, RR.termType), None)
    datatype = next(mapping_graph.objects(object_map, RR.datatype), None)
    if constant is not None:
        return URIRef(str(constant)) if term_type == RR.IRI or isinstance(constant, URIRef) else constant
    if template is not None:
        value = _format_template(str(template), row)
        return URIRef(value) if term_type == RR.IRI else Literal(value, datatype=datatype)
    if column is not None:
        value = row.get(str(column))
        if value in (None, ""):
            return None
        return URIRef(str(value)) if term_type == RR.IRI else Literal(value, datatype=datatype)
    return None


def create_execution_provenance(
    *,
    mapping_iri: URIRef,
    source_dataset: URIRef,
    target_graph: URIRef,
    record_count: int,
    executor: URIRef = URIRef("https://example.org/semantic-platform/provenance#platformAgent"),
) -> Graph:
    """Create PROV-O provenance for a mapping execution."""
    graph = Graph()
    now = datetime.now(UTC).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    execution = URIRef(f"https://example.org/mapping-execution/{Path(str(mapping_iri)).name}-{stamp}")
    generated = URIRef(f"https://example.org/generated-dataset/{Path(str(mapping_iri)).name}-{stamp}")
    graph.add((execution, RDF.type, MAP.MappingExecution))
    graph.add((execution, MAP.usesMapping, mapping_iri))
    graph.add((execution, MAP.sourcedFrom, source_dataset))
    graph.add((execution, MAP.executedBy, executor))
    graph.add((execution, MAP.generatedGraph, target_graph))
    graph.add((execution, MAP.generatedEntity, generated))
    graph.add((execution, MAP.recordCount, Literal(record_count, datatype=XSD.integer)))
    graph.add((execution, PROV.startedAtTime, Literal(now, datatype=XSD.dateTime)))
    graph.add((execution, PROV.endedAtTime, Literal(now, datatype=XSD.dateTime)))
    graph.add((execution, PROV.wasAssociatedWith, executor))
    graph.add((execution, PROV.used, source_dataset))
    graph.add((generated, RDF.type, PROV.Entity))
    graph.add((generated, RDF.type, SP.Dataset))
    graph.add((generated, RDFS.label, Literal("Generated RDF dataset")))
    graph.add((generated, PROV.wasGeneratedBy, execution))
    graph.add((generated, PROV.wasDerivedFrom, source_dataset))
    return graph


def execute_mapping_workflow(
    mapping_path: Path | str,
    rows: list[dict[str, Any]],
    *,
    source_dataset: URIRef | None = None,
    target_graph: URIRef | None = None,
) -> MappingExecutionResult:
    """Validate a mapping, generate RDF from rows, and append provenance."""
    mapping_graph = load_r2rml_mapping(mapping_path)
    validation = validate_mapping(mapping_graph)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    triples_map = next(mapping_graph.subjects(RDF.type, RR.TriplesMap))
    source_dataset = source_dataset or next(mapping_graph.objects(triples_map, MAP.sourcedFrom))
    target_graph = target_graph or next(mapping_graph.objects(triples_map, MAP.targetGraph))
    output = generate_rdf_from_rows(mapping_graph, rows, source_dataset=source_dataset)
    provenance = create_execution_provenance(
        mapping_iri=triples_map,
        source_dataset=source_dataset,
        target_graph=target_graph,
        record_count=len(rows),
    )
    output += provenance
    execution = next(provenance.subjects(RDF.type, MAP.MappingExecution))
    return MappingExecutionResult(graph=output, execution_iri=execution, triple_count=len(output))


def validate_all_mappings(settings: Settings | None = None) -> dict[str, MappingValidationResult]:
    """Validate all repository R2RML mapping files."""
    return {str(path): validate_mapping_file(path) for path in mapping_files(settings)}
