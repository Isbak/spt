"""Tests for generic drop-in R2RML source materialization."""

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

# A pre-existing, domain-neutral example mapping used to exercise the generic
# materialization path (queries the `dataset` table from mappings/sql/).
EXAMPLE_MAPPING = "mappings/r2rml/example_dataset.ttl"


def _settings_with_output(tmp_path):
    return dataclasses.replace(load_settings(), output_dir=tmp_path / "output")


def test_r2rml_and_ttl_extensions_are_discovered(tmp_path):
    (tmp_path / "a.ttl").write_text("", encoding="utf-8")
    (tmp_path / "b.r2rml").write_text("", encoding="utf-8")
    settings = dataclasses.replace(load_settings(), r2rml_dir=tmp_path)
    names = {path.name for path in mapping_files(settings)}
    assert names == {"a.ttl", "b.r2rml"}


def test_logical_table_sql_supports_query_and_table():
    graph = load_r2rml_mapping(EXAMPLE_MAPPING)
    triples_map = next(graph.subjects(RDF.type, RR.TriplesMap))
    assert "FROM dataset" in logical_table_sql(graph, triples_map)

    table_graph = Graph()
    table_graph.parse(
        data="""
        @prefix rr: <http://www.w3.org/ns/r2rml#> .
        <urn:m> a rr:TriplesMap ; rr:logicalTable [ rr:tableName "widgets" ] .
        """,
        format="turtle",
    )
    tm = next(table_graph.subjects(RDF.type, RR.TriplesMap))
    assert logical_table_sql(table_graph, tm) == 'SELECT * FROM "widgets"'


def test_logical_table_sql_delimits_qualified_and_special_table_names():
    """Schema-qualified or non-bare table names must not break SQL syntax.

    A bare ``SELECT * FROM <name>`` crashes with ``near ".": syntax error`` (or
    similar) when the name is schema-qualified or contains spaces/hyphens; the
    name has to be delimited.
    """
    cases = {
        "app.person": 'SELECT * FROM "app"."person"',
        "people-v2": 'SELECT * FROM "people-v2"',
        "Order Details": 'SELECT * FROM "Order Details"',
        '"already"."quoted"': 'SELECT * FROM "already"."quoted"',
        "(SELECT 1)": "SELECT * FROM (SELECT 1)",
    }
    for table_name, expected in cases.items():
        graph = Graph()
        graph.parse(
            data=f"""
            @prefix rr: <http://www.w3.org/ns/r2rml#> .
            <urn:m> a rr:TriplesMap ; rr:logicalTable [ rr:tableName {table_name!r} ] .
            """,
            format="turtle",
        )
        tm = next(graph.subjects(RDF.type, RR.TriplesMap))
        assert logical_table_sql(graph, tm) == expected

    # The delimited form executes cleanly against SQLite instead of raising.
    source = SqliteRowSource.from_sql_files([])
    source._connection.executescript(
        'CREATE TABLE "people-v2" (id TEXT); INSERT INTO "people-v2" VALUES (\'p1\');'
    )
    assert source.fetch('SELECT * FROM "people-v2"') == [{"id": "p1"}]


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

    base = load_settings()
    settings = dataclasses.replace(
        base,
        source_business=dataclasses.replace(base.source_business, database_url=f"sqlite:///{db_path}"),
    )
    source = resolve_row_source(settings)
    try:
        assert source.fetch("SELECT id FROM item") == [{"id": "x"}]
    finally:
        source.close()


def test_materialize_mapping_writes_output(tmp_path):
    settings = _settings_with_output(tmp_path)
    source = resolve_row_source(settings)
    try:
        result = materialize_mapping(EXAMPLE_MAPPING, source, settings)
    finally:
        source.close()
    assert result.record_count == 2
    assert result.triple_count > 0
    assert result.target_graph == "urn:graph:integration"
    assert result.output_path.exists()

    materialized = Graph()
    materialized.parse(result.output_path, format="turtle")
    assert (
        URIRef("https://example.org/resource/dataset/DS-001"),
        None,
        None,
    ) in materialized


def test_materialize_mappings_covers_all_files(tmp_path):
    settings = _settings_with_output(tmp_path)
    results = materialize_mappings(settings)
    by_name = {result.mapping_path.name: result for result in results}
    assert "example_dataset.ttl" in by_name
    assert by_name["example_dataset.ttl"].record_count == 2
    assert all(result.triple_count > 0 for result in results)


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
    client = _FakeClient(ok=True, count=26)
    counts = fuseki_graph_triple_counts(["urn:graph:integration"], client=client)
    assert counts == {"urn:graph:integration": 26}
    assert client.queries  # a COUNT query was issued per graph


def test_fuseki_graph_triple_counts_empty_when_unavailable():
    client = _FakeClient(ok=False)
    assert fuseki_graph_triple_counts(["urn:graph:integration"], client=client) == {}


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
    assert any(r.mapping_path.name == "example_dataset.ttl" for r in results)
    loads = load_sources_into_fuseki()
    # Fuseki is unreachable in tests, so loads are skipped, not failed.
    assert loads and not any(load.loaded for load in loads)


def test_materialization_route(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("FUSEKI_BASE_URL", "http://localhost:65535")
    client = create_app().test_client()
    response = client.get("/materialization")
    assert response.status_code == 200
    assert b"Source Materialization" in response.data


# --- Symmetric per-role routing (ADR-0017) -----------------------------------------

def _mapping_ttl(name: str, target_graph: str) -> str:
    return f"""
    @prefix rr: <http://www.w3.org/ns/r2rml#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix sp: <https://example.org/semantic-platform/core#> .
    @prefix map: <https://example.org/semantic-platform/mappings#> .
    @prefix gov: <https://example.org/semantic-platform/governance#> .

    <https://example.org/mapping/{name}>
        a rr:TriplesMap, map:Mapping ;
        rr:logicalTable [ rr:sqlQuery "SELECT id FROM t" ] ;
        rr:subjectMap [ rr:template "https://example.org/resource/{name}/{{id}}" ; rr:class sp:Resource ;
                        rr:graph <{target_graph}> ] ;
        rr:predicateObjectMap [ rr:predicate sp:identifier ;
                                rr:objectMap [ rr:column "id" ; rr:datatype xsd:string ] ] ;
        map:sourcedFrom <https://example.org/source/{name}> ;
        map:targetGraph <{target_graph}> ;
        map:version "1.0.0" ;
        gov:hasOwner gov:platformOwner ;
        gov:hasSteward gov:platformSteward .
    """


class _RoleRecordingSource:
    def __init__(self, role: str) -> None:
        self.role = role

    def fetch(self, sql: str):
        return [{"id": self.role}]

    def close(self) -> None:
        pass


def test_materialize_mappings_reads_each_mapping_from_its_role_source(tmp_path, monkeypatch):
    r2rml = tmp_path / "r2rml"
    r2rml.mkdir()
    (r2rml / "biz.ttl").write_text(_mapping_ttl("biz", "urn:graph:integration"), encoding="utf-8")
    (r2rml / "agt.ttl").write_text(_mapping_ttl("agt", "urn:graph:agents"), encoding="utf-8")
    settings = dataclasses.replace(load_settings(), r2rml_dir=r2rml, output_dir=tmp_path / "out")

    requested: list[str] = []

    def fake_resolve(settings_arg, role="business"):
        requested.append(role)
        return _RoleRecordingSource(role)

    monkeypatch.setattr("semantic_platform.materialize.resolve_row_source", fake_resolve)
    results = materialize_mappings(settings)

    by_graph = {r.target_graph: r for r in results}
    # Each mapping was fed from the source for its target graph's role.
    assert set(requested) == {"business", "agents"}
    assert by_graph["urn:graph:integration"].record_count == 1
    assert by_graph["urn:graph:agents"].record_count == 1


def test_push_to_fuseki_routes_each_graph_to_its_role_dataset(tmp_path, monkeypatch):
    from semantic_platform.materialize import FusekiLoadResult, MaterializationResult  # noqa: F401

    results = [
        MaterializationResult(tmp_path / "biz.ttl", "urn:m:biz", "urn:graph:integration", 1, 1, tmp_path / "biz.ttl"),
        MaterializationResult(tmp_path / "agt.ttl", "urn:m:agt", "urn:graph:agents", 1, 1, tmp_path / "agt.ttl"),
    ]
    for item in results:
        item.output_path.write_text("", encoding="utf-8")

    constructed: list[str] = []

    class _RoleClient:
        def __init__(self, settings=None, dataset="system", **kwargs):
            self.dataset = dataset
            constructed.append(dataset)
            self.uploads: list[str] = []

        def health_check(self):
            return FusekiStatus(True, 200, "ok")

        def upload_graph(self, file_path, graph_uri):
            self.uploads.append(graph_uri)

    monkeypatch.setattr("semantic_platform.materialize.FusekiClient", _RoleClient)
    loads = push_to_fuseki(results, settings=load_settings())

    assert all(load.loaded for load in loads)
    # Distinct datasets were used for the two roles.
    assert set(constructed) == {"business", "agents"}
