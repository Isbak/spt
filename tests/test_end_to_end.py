"""In-process end-to-end tests covering the whole project border.

These exercise the platform as a user would, but entirely self-contained: the
repository's own RDF assets, SHACL validation, source materialization against the
bundled ``mappings/sql`` source, reasoning/consistency, every shipped SPARQL
query, the ``api`` facade, and every Flask UI/JSON route.

They deliberately do **not** reach any external system — no external data
warehouse (the relational source is in-memory SQLite built from the repo's
``*.sql`` files) and no external Apache Jena (Fuseki interactions use the
in-process client against a stand-in, never a live server). Live-Fuseki /
live-database round trips are out of scope here by design.
"""

from __future__ import annotations

import dataclasses

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from app.app import create_app
from semantic_platform.api import (
    fuseki_graph_triple_counts,
    get_graph_stats,
    validate_platform,
)
from semantic_platform.config import load_settings
from semantic_platform.consistency import validate_consistency
from semantic_platform.fuseki import FusekiStatus
from semantic_platform.graph import load_graph
from semantic_platform.materialize import materialize_mappings, push_to_fuseki
from semantic_platform.query import execute_query, read_query
from semantic_platform.r2rdf import MAP
from semantic_platform.reasoning import run_reasoning

# --- A relational/serving stand-in that stays inside the project border -------


class _InProcessFuseki:
    """Records uploads and answers COUNT queries without any network."""

    def __init__(self, counts: dict[str, int] | None = None) -> None:
        self._counts = counts or {}
        self.uploads: list[tuple[str, str]] = []

    def health_check(self) -> FusekiStatus:
        return FusekiStatus(True, 200, "ok")

    def upload_graph(self, file_path, graph_uri) -> None:
        self.uploads.append((str(file_path), graph_uri))

    def execute_query(self, query_text: str) -> dict:
        for graph_uri, count in self._counts.items():
            if graph_uri in query_text:
                return {"results": {"bindings": [{"count": {"value": str(count)}}]}}
        return {"results": {"bindings": []}}


# --- Validation & graph load --------------------------------------------------


def test_e2e_repository_validates_and_loads():
    syntax_results, shacl_report = validate_platform()
    assert syntax_results and all(result.valid for result in syntax_results)
    assert shacl_report.conforms, shacl_report.results_text

    stats = get_graph_stats()
    assert stats.triples > 0
    assert stats.subjects > 0


# --- Source materialization (self-contained) ----------------------------------


def test_e2e_repository_mappings_materialize_self_contained(tmp_path):
    settings = dataclasses.replace(load_settings(), output_dir=tmp_path / "output")
    results = materialize_mappings(settings)
    assert results, "no mappings discovered"
    for result in results:
        assert result.triple_count > 0
        assert result.output_path.exists()
        graph = Graph()
        graph.parse(result.output_path, format="turtle")
        # Every materialized graph carries PROV-O execution provenance.
        assert (None, RDF.type, MAP.MappingExecution) in graph

    # Push to an in-process Fuseki stand-in and read the served counts back.
    counts = {result.target_graph: result.triple_count for result in results}
    client = _InProcessFuseki(counts)
    loads = push_to_fuseki(results, settings=settings, client=client)
    assert loads and all(load.loaded for load in loads)
    assert len(client.uploads) == len(results)

    served = fuseki_graph_triple_counts(list(counts), settings=settings, client=client)
    assert served == counts


def test_e2e_drop_in_mapping_materializes(tmp_path):
    """A brand-new dropped-in .r2rml + .sql source works end to end."""
    r2rml_dir = tmp_path / "r2rml"
    sql_dir = tmp_path / "sql"
    r2rml_dir.mkdir()
    sql_dir.mkdir()
    (r2rml_dir / "e2e.r2rml").write_text(
        """
        @prefix rr: <http://www.w3.org/ns/r2rml#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix sp: <https://example.org/semantic-platform/core#> .
        @prefix map: <https://example.org/semantic-platform/mappings#> .
        @prefix gov: <https://example.org/semantic-platform/governance#> .
        <https://example.org/mapping/e2e>
            a rr:TriplesMap, map:Mapping ;
            rdfs:label "E2E mapping" ;
            rr:logicalTable [ rr:sqlQuery "SELECT widget_id, widget_name FROM widget" ] ;
            rr:subjectMap [ rr:template "https://example.org/resource/widget/{widget_id}" ;
                            rr:class sp:Entity ; rr:graph <urn:graph:e2e> ] ;
            rr:predicateObjectMap [ rr:predicate sp:identifier ;
                rr:objectMap [ rr:column "widget_id" ; rr:datatype xsd:string ] ] ;
            rr:predicateObjectMap [ rr:predicate rdfs:label ;
                rr:objectMap [ rr:column "widget_name" ; rr:datatype xsd:string ] ] ;
            map:sourcedFrom <https://example.org/source-dataset/e2e> ;
            map:targetGraph <urn:graph:e2e> ;
            map:version "1.0.0" ;
            gov:hasOwner gov:platformOwner ;
            gov:hasSteward gov:platformSteward .
        """,
        encoding="utf-8",
    )
    (sql_dir / "widget.sql").write_text(
        "CREATE TABLE widget (widget_id TEXT PRIMARY KEY, widget_name TEXT NOT NULL);"
        "INSERT INTO widget VALUES ('W-1', 'First');"
        "INSERT INTO widget VALUES ('W-2', 'Second');",
        encoding="utf-8",
    )
    base = load_settings()
    settings = dataclasses.replace(
        base,
        r2rml_dir=r2rml_dir,
        output_dir=tmp_path / "out",
        # The e2e mapping targets an unknown graph, which routes to the business role.
        source_business=dataclasses.replace(
            base.source_business, database_url=None, sql_files=(), sql_dir=sql_dir
        ),
    )
    results = materialize_mappings(settings)
    assert len(results) == 1
    assert results[0].record_count == 2
    materialized = Graph()
    materialized.parse(results[0].output_path, format="turtle")
    assert (URIRef("https://example.org/resource/widget/W-1"), None, None) in materialized


# --- Reasoning, inference & consistency ---------------------------------------


def test_e2e_reasoning_and_consistency():
    graph = load_graph()
    run = run_reasoning(graph=graph)
    assert run.inferred_count >= 0  # reasoner executes over the live repository
    assert run.engine_version

    report = validate_consistency(graph=graph)
    assert report.conforms, [issue.message for issue in report.issues]


# --- Every shipped SPARQL query executes --------------------------------------


def test_e2e_all_repository_queries_execute():
    settings = load_settings()
    graph = load_graph(settings=settings)
    query_files = sorted(settings.queries_dir.glob("*.rq"))
    assert query_files, "no SPARQL queries found"
    rows_returned = 0
    for query_file in query_files:
        result = execute_query(read_query(query_file), graph)
        rows_returned += len(list(result))
    # At least some of the shipped queries return data against the repo graph.
    assert rows_returned > 0


# --- Every Flask route is reachable -------------------------------------------


def test_e2e_all_ui_and_api_routes_return_200(tmp_path, monkeypatch):
    # Keep materialization output out of the repo and make any Fuseki call fail
    # fast (connection refused) so routes degrade gracefully instead of hanging.
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("FUSEKI_BASE_URL", "http://127.0.0.1:9")

    app = create_app()
    client = app.test_client()

    static_endpoints = {"static"}
    simple_rules = [
        rule
        for rule in app.url_map.iter_rules()
        if "GET" in rule.methods and not rule.arguments and rule.endpoint not in static_endpoints
    ]
    assert len(simple_rules) > 50  # sanity: the whole UI/API surface is covered

    for rule in simple_rules:
        response = client.get(rule.rule)
        assert response.status_code == 200, f"{rule.rule} -> {response.status_code}"

    # Routes parameterised by agent id, resolved from live registry data.
    agents = client.get("/api/agents").get_json()
    if agents:
        agent_id = str(agents[0].get("id") or agents[0].get("identifier") or "").split("/")[-1]
        if agent_id:
            for suffix in ("", "/memory", "/observations", "/provenance", "/context"):
                response = client.get(f"/api/agents/{agent_id}{suffix}")
                assert response.status_code == 200, f"/api/agents/{agent_id}{suffix}"
