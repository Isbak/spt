"""Tests for drop-in R2RML materialization (install-base use case)."""

from __future__ import annotations

import dataclasses
import sqlite3

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from app.app import create_app
from semantic_platform.api import (
    fuseki_graph_triple_counts,
    load_sources_into_fuseki,
    materialize_sources,
)
from semantic_platform.config import load_settings
from semantic_platform.fuseki import FusekiStatus
from semantic_platform.materialize import (
    SqliteRowSource,
    materialize_mapping,
    materialize_mappings,
    push_to_fuseki,
    resolve_row_source,
)
from semantic_platform.r2rdf import RR, load_r2rml_mapping, logical_table_sql, mapping_files


def _settings_with_output(tmp_path):
    return dataclasses.replace(load_settings(), output_dir=tmp_path / "output")


def test_r2rml_extension_is_discovered():
    names = {path.name for path in mapping_files()}
    assert "install-base.r2rml" in names


def test_logical_table_sql_supports_query_and_table():
    graph = load_r2rml_mapping("mappings/r2rml/install-base.r2rml")
    triples_map = next(graph.subjects(RDF.type, RR.TriplesMap))
    assert "FROM install_base" in logical_table_sql(graph, triples_map)

    table_graph = Graph()
    table_graph.parse(
        data="""
        @prefix rr: <http://www.w3.org/ns/r2rml#> .
        <urn:m> a rr:TriplesMap ; rr:logicalTable [ rr:tableName "widgets" ] .
        """,
        format="turtle",
    )
    tm = next(table_graph.subjects(RDF.type, RR.TriplesMap))
    assert logical_table_sql(table_graph, tm) == "SELECT * FROM widgets"


def test_logical_table_sql_requires_source():
    graph = Graph()
    graph.parse(
        data="""
        @prefix rr: <http://www.w3.org/ns/r2rml#> .
        <urn:m> a rr:TriplesMap ; rr:logicalTable [] .
        """,
        format="turtle",
    )
    tm = next(graph.subjects(RDF.type, RR.TriplesMap))
    with pytest.raises(ValueError):
        logical_table_sql(graph, tm)


def test_sqlite_row_source_from_sql_files_orders_schema_first(tmp_path):
    data = tmp_path / "data.sql"
    data.write_text("INSERT INTO t VALUES ('a');", encoding="utf-8")
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE t (id TEXT);", encoding="utf-8")
    source = SqliteRowSource.from_sql_files([data, schema])
    try:
        assert source.fetch("SELECT id FROM t") == [{"id": "a"}]
    finally:
        source.close()


def test_resolve_row_source_sqlite_file(tmp_path):
    db_path = tmp_path / "live.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE item (id TEXT)")
    connection.execute("INSERT INTO item VALUES ('x')")
    connection.commit()
    connection.close()

    settings = dataclasses.replace(load_settings(), source_database_url=f"sqlite:///{db_path}")
    source = resolve_row_source(settings)
    try:
        assert source.fetch("SELECT id FROM item") == [{"id": "x"}]
    finally:
        source.close()


def test_materialize_mapping_writes_output(tmp_path):
    settings = _settings_with_output(tmp_path)
    source = resolve_row_source(settings)
    try:
        result = materialize_mapping("mappings/r2rml/install-base.r2rml", source, settings)
    finally:
        source.close()
    assert result.record_count == 3
    assert result.triple_count > 0
    assert result.target_graph == "urn:graph:install-base"
    assert result.output_path.exists()

    materialized = Graph()
    materialized.parse(result.output_path, format="turtle")
    assert (
        URIRef("https://example.org/resource/install-base/IB-001"),
        None,
        None,
    ) in materialized


def test_materialize_mappings_covers_all_files(tmp_path):
    settings = _settings_with_output(tmp_path)
    results = materialize_mappings(settings)
    by_name = {result.mapping_path.name: result for result in results}
    assert "install-base.r2rml" in by_name
    assert by_name["install-base.r2rml"].record_count == 3


def test_materialize_mapping_rejects_invalid_mapping(tmp_path):
    bad = tmp_path / "bad.r2rml"
    bad.write_text(
        """
        @prefix rr: <http://www.w3.org/ns/r2rml#> .
        <urn:m> a rr:TriplesMap ; rr:logicalTable [ rr:tableName "t" ] .
        """,
        encoding="utf-8",
    )
    settings = _settings_with_output(tmp_path)
    source = SqliteRowSource(sqlite3.connect(":memory:"))
    try:
        with pytest.raises(ValueError):
            materialize_mapping(bad, source, settings)
    finally:
        source.close()


class _FakeClient:
    def __init__(self, ok: bool, count: int = 0) -> None:
        self._ok = ok
        self._count = count
        self.uploads: list[tuple[str, str]] = []
        self.queries: list[str] = []

    def health_check(self) -> FusekiStatus:
        return FusekiStatus(self._ok, 200 if self._ok else None, "ok" if self._ok else "down")

    def upload_graph(self, file_path, graph_uri) -> None:
        self.uploads.append((str(file_path), graph_uri))

    def execute_query(self, query_text: str) -> dict:
        self.queries.append(query_text)
        return {"results": {"bindings": [{"count": {"value": str(self._count)}}]}}


def test_fuseki_graph_triple_counts_reads_back_when_available():
    client = _FakeClient(ok=True, count=37)
    counts = fuseki_graph_triple_counts(["urn:graph:install-base"], client=client)
    assert counts == {"urn:graph:install-base": 37}
    assert client.queries  # a COUNT query was issued per graph


def test_fuseki_graph_triple_counts_empty_when_unavailable():
    client = _FakeClient(ok=False)
    assert fuseki_graph_triple_counts(["urn:graph:install-base"], client=client) == {}


def test_push_to_fuseki_loads_when_available(tmp_path):
    settings = _settings_with_output(tmp_path)
    results = materialize_mappings(settings)
    client = _FakeClient(ok=True)
    loads = push_to_fuseki(results, settings=settings, client=client)
    assert loads and all(load.loaded for load in loads)
    assert len(client.uploads) == len(results)


def test_push_to_fuseki_skips_when_unavailable(tmp_path):
    settings = _settings_with_output(tmp_path)
    results = materialize_mappings(settings)
    client = _FakeClient(ok=False)
    loads = push_to_fuseki(results, settings=settings, client=client)
    assert loads and not any(load.loaded for load in loads)
    assert client.uploads == []


def test_api_materialize_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("FUSEKI_BASE_URL", "http://localhost:65535")
    results = materialize_sources()
    assert any(r.mapping_path.name == "install-base.r2rml" for r in results)
    loads = load_sources_into_fuseki()
    # Fuseki is unreachable in tests, so loads are skipped, not failed.
    assert loads and not any(load.loaded for load in loads)


def test_install_base_route(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("FUSEKI_BASE_URL", "http://localhost:65535")
    client = create_app().test_client()
    response = client.get("/install-base")
    assert response.status_code == 200
    assert b"Install Base Materialization" in response.data
    assert b"install-base" in response.data
