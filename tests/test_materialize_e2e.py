"""End-to-end tests for the drop-in source materialization workflow.

`test_end_to_end_drop_in_workflow` exercises the whole user-facing scenario in
one pass with no network: author a brand-new `.r2rml` mapping and a self-contained
`.sql` source on disk, discover and materialize them, then push to Fuseki and read
back the served triple counts. `test_live_fuseki_round_trip` performs the same
load/query against a real Apache Jena instance and is skipped unless
``RUN_FUSEKI_E2E=1`` is set with a reachable server (e.g. after ``make docker-up``).
"""

from __future__ import annotations

import dataclasses
import os

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from semantic_platform.api import fuseki_graph_triple_counts
from semantic_platform.config import load_settings
from semantic_platform.fuseki import FusekiClient, FusekiStatus
from semantic_platform.materialize import materialize_mappings, push_to_fuseki
from semantic_platform.r2rdf import MAP

MAPPING_TTL = """
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
"""

SOURCE_SQL = """
CREATE TABLE widget (widget_id TEXT PRIMARY KEY, widget_name TEXT NOT NULL);
INSERT INTO widget VALUES ('W-1', 'First widget');
INSERT INTO widget VALUES ('W-2', 'Second widget');
"""


class _RecordingClient:
    """Stand-in Fuseki client that records uploads and answers count queries."""

    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts
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


def test_end_to_end_drop_in_workflow(tmp_path):
    # 1. A user "drops in" a .r2rml mapping and a self-contained .sql source.
    r2rml_dir = tmp_path / "r2rml"
    sql_dir = tmp_path / "sql"
    output_dir = tmp_path / "output"
    r2rml_dir.mkdir()
    sql_dir.mkdir()
    (r2rml_dir / "e2e.r2rml").write_text(MAPPING_TTL, encoding="utf-8")
    (sql_dir / "widget.sql").write_text(SOURCE_SQL, encoding="utf-8")

    settings = dataclasses.replace(
        load_settings(),
        r2rml_dir=r2rml_dir,
        sql_dir=sql_dir,
        output_dir=output_dir,
        source_database_url=None,
        source_sql_files=(),
    )

    # 2. Discover + materialize against the self-contained source.
    results = materialize_mappings(settings)
    assert len(results) == 1
    result = results[0]
    assert result.mapping_path.name == "e2e.r2rml"
    assert result.record_count == 2
    assert result.target_graph == "urn:graph:e2e"
    assert result.output_path.exists()

    # 3. The materialized RDF holds the mapped rows and PROV-O provenance.
    materialized = Graph()
    materialized.parse(result.output_path, format="turtle")
    assert (URIRef("https://example.org/resource/widget/W-1"), None, None) in materialized
    assert (None, RDF.type, MAP.MappingExecution) in materialized

    # 4. Push to (a stand-in) Fuseki and confirm it is served via read-back.
    client = _RecordingClient({"urn:graph:e2e": result.triple_count})
    loads = push_to_fuseki(results, settings=settings, client=client)
    assert [load.target_graph for load in loads] == ["urn:graph:e2e"]
    assert client.uploads == [(str(result.output_path), "urn:graph:e2e")]

    counts = fuseki_graph_triple_counts(["urn:graph:e2e"], settings=settings, client=client)
    assert counts == {"urn:graph:e2e": result.triple_count}


@pytest.mark.skipif(
    os.getenv("RUN_FUSEKI_E2E") != "1",
    reason="Set RUN_FUSEKI_E2E=1 with a reachable Fuseki (make docker-up) to run the live round trip.",
)
def test_live_fuseki_round_trip(tmp_path):
    client = FusekiClient()
    assert client.health_check().ok, "Fuseki is not reachable"
    graph_uri = "urn:graph:e2e-live"
    ttl = tmp_path / "graph.ttl"
    ttl.write_text(
        "@prefix ex: <https://example.org/> . ex:s ex:p ex:o . ex:s ex:q ex:r .",
        encoding="utf-8",
    )
    client.upload_graph(ttl, graph_uri)
    counts = fuseki_graph_triple_counts([graph_uri], client=client)
    assert counts == {graph_uri: 2}
