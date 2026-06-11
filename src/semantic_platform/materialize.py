"""Drop-in materialization of R2RML mappings into RDF and Fuseki.

This module turns a mapping file (``mappings/r2rml/*.r2rml`` or ``*.ttl``) plus a
relational source into materialized RDF without any per-mapping code. A user
drops a Turtle data file in ``rdf/data/`` and an R2RML mapping in
``mappings/r2rml/``; ``materialize_mappings`` then reads each mapping's
``rr:logicalTable`` query, runs it against the configured :class:`RowSource`,
generates RDF with PROV-O provenance, and writes one Turtle file per mapping to
``output/``. :func:`push_to_fuseki` loads those graphs into their declared
``map:targetGraph`` named graphs so the result is queryable in the Flask UI.

Two source modes are supported, matching the two deployment use cases:

* **Self-contained** — no ``SOURCE_DATABASE_URL``. The mapping queries run
  against an in-memory SQLite database built from the ``*.sql`` files in
  ``mappings/sql/`` ("the system here is used").
* **Live data platform** — ``SOURCE_DATABASE_URL`` points at an external
  relational database; queries run against it directly.

The module is deliberately domain-neutral: it carries no assumptions about what
the mappings describe.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any, Protocol, runtime_checkable

from rdflib.namespace import RDF

from semantic_platform.config import Settings, load_settings
from semantic_platform.fuseki import FusekiClient
from semantic_platform.r2rdf import (
    MAP,
    RR,
    execute_mapping_workflow,
    load_r2rml_mapping,
    logical_table_sql,
    mapping_files,
    validate_mapping,
)


@runtime_checkable
class RowSource(Protocol):
    """A relational source that can answer a SQL query with row dictionaries."""

    def fetch(self, sql: str) -> list[dict[str, Any]]:
        """Execute ``sql`` and return the result rows as dictionaries."""

    def close(self) -> None:
        """Release any resources held by the source."""


class SqliteRowSource:
    """A :class:`RowSource` backed by a SQLite connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        self._connection = connection

    @classmethod
    def from_sql_files(cls, sql_files: list[Path]) -> SqliteRowSource:
        """Build an in-memory database from schema/data ``*.sql`` files.

        Files whose name contains ``schema`` are executed first so that table
        definitions precede inserts regardless of discovery order.
        """
        connection = sqlite3.connect(":memory:")
        ordered = sorted(sql_files, key=lambda path: (0 if "schema" in path.name else 1, path.name))
        for path in ordered:
            connection.executescript(Path(path).read_text(encoding="utf-8"))
        return cls(connection)

    @classmethod
    def from_database_file(cls, path: Path | str) -> SqliteRowSource:
        """Open a SQLite database file as a row source."""
        return cls(sqlite3.connect(str(path)))

    def fetch(self, sql: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._connection.execute(sql).fetchall()]

    def close(self) -> None:
        self._connection.close()


def _sql_files(settings: Settings) -> list[Path]:
    """Return the SQL files used to build the self-contained source."""
    if settings.source_sql_files:
        return [path for path in settings.source_sql_files if path.exists()]
    if not settings.sql_dir.exists():
        return []
    return sorted(settings.sql_dir.glob("*.sql"))


def resolve_row_source(settings: Settings | None = None) -> RowSource:
    """Resolve the configured relational source.

    Uses ``SOURCE_DATABASE_URL`` when set (live data platform); otherwise builds
    a self-contained in-memory SQLite database from ``mappings/sql/*.sql``.
    """
    settings = settings or load_settings()
    url = settings.source_database_url
    if not url:
        return SqliteRowSource.from_sql_files(_sql_files(settings))
    if url.startswith("sqlite:///"):
        return SqliteRowSource.from_database_file(url.removeprefix("sqlite:///"))
    if url.startswith("sqlite://"):  # in-memory sqlite:// URL
        return SqliteRowSource.from_sql_files(_sql_files(settings))
    return _sqlalchemy_source(url)


def _sqlalchemy_source(url: str) -> RowSource:  # pragma: no cover - requires a live database
    """Wrap any SQLAlchemy-supported database as a row source (lazy import)."""
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:  # pragma: no cover - exercised only without sqlalchemy
        raise RuntimeError(
            "SOURCE_DATABASE_URL points at a non-SQLite database; install the "
            "'sqlalchemy' extra and the appropriate driver to use a live data platform."
        ) from exc

    class _SqlAlchemyRowSource:
        def __init__(self, database_url: str) -> None:
            self._engine = create_engine(database_url)

        def fetch(self, sql: str) -> list[dict[str, Any]]:
            with self._engine.connect() as connection:
                result = connection.execute(text(sql))
                return [dict(row) for row in result.mappings()]

        def close(self) -> None:
            self._engine.dispose()

    return _SqlAlchemyRowSource(url)


@dataclass(frozen=True)
class MaterializationResult:
    """Outcome of materializing a single mapping file."""

    mapping_path: Path
    mapping_iri: str
    target_graph: str
    record_count: int
    triple_count: int
    output_path: Path


def materialize_mapping(
    mapping_path: Path | str,
    source: RowSource,
    settings: Settings | None = None,
) -> MaterializationResult:
    """Materialize one mapping file into a Turtle graph written to ``output/``."""
    settings = settings or load_settings()
    mapping_path = Path(mapping_path)
    mapping_graph = load_r2rml_mapping(mapping_path)
    validation = validate_mapping(mapping_graph)
    if not validation.valid:
        raise ValueError(f"{mapping_path.name}: {'; '.join(validation.errors)}")

    triples_map = next(mapping_graph.subjects(RDF.type, RR.TriplesMap))
    rows = source.fetch(logical_table_sql(mapping_graph, triples_map))
    result = execute_mapping_workflow(mapping_path, rows)
    target_graph = str(next(mapping_graph.objects(triples_map, MAP.targetGraph)))

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.output_dir / f"{mapping_path.stem}.ttl"
    result.graph.serialize(destination=output_path, format="turtle")

    return MaterializationResult(
        mapping_path=mapping_path,
        mapping_iri=str(triples_map),
        target_graph=target_graph,
        record_count=len(rows),
        triple_count=result.triple_count,
        output_path=output_path,
    )


def materialize_mappings(settings: Settings | None = None) -> list[MaterializationResult]:
    """Materialize every discovered mapping file against the configured source."""
    settings = settings or load_settings()
    source = resolve_row_source(settings)
    try:
        return [materialize_mapping(path, source, settings) for path in mapping_files(settings)]
    finally:
        source.close()


@dataclass(frozen=True)
class FusekiLoadResult:
    """Outcome of pushing a materialized graph to Fuseki."""

    target_graph: str
    output_path: Path
    loaded: bool
    message: str


def push_to_fuseki(
    results: list[MaterializationResult],
    settings: Settings | None = None,
    client: FusekiClient | None = None,
) -> list[FusekiLoadResult]:
    """Upload materialized graphs into their ``map:targetGraph`` named graphs.

    Best-effort: when Fuseki is unreachable the load is skipped (not failed) so
    local materialization and CI remain green without a running server.
    """
    settings = settings or load_settings()
    client = client or FusekiClient(settings=settings)
    status = client.health_check()
    if not status.ok:
        return [
            FusekiLoadResult(item.target_graph, item.output_path, False, f"Fuseki unavailable: {status.message}")
            for item in results
        ]
    loads: list[FusekiLoadResult] = []
    for item in results:
        client.upload_graph(item.output_path, item.target_graph)
        loads.append(FusekiLoadResult(item.target_graph, item.output_path, True, "loaded"))
    return loads
