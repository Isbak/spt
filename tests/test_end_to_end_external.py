"""End-to-end test of the EXTERNAL integration mode (simulated).

The companion suite in ``test_end_to_end.py`` runs fully self-contained. This
one exercises the *external* code paths instead — materializing from an external
data warehouse and serving into an external Apache Jena/Fuseki — but without
needing any real external service:

* **External warehouse (Snowflake-style)** — a file-backed database reached
  through ``SOURCE_DATABASE_URL``. This is the exact resolver/serialization path
  a real warehouse uses; swapping in ``snowflake://...`` (plus the Snowflake
  SQLAlchemy driver) changes only the connection URL.
* **External Apache Jena** — a local HTTP server emulating Fuseki's Graph Store
  Protocol (PUT) and SPARQL query endpoint, so the real ``FusekiClient`` performs
  genuine HTTP uploads and read-back queries over the network stack.

This mirrors the configuration produced by uncommenting the external-integration
variables in ``.env``; with them commented out the platform runs self-contained.
"""

from __future__ import annotations

import dataclasses
import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from semantic_platform.api import fuseki_graph_triple_counts
from semantic_platform.config import load_settings
from semantic_platform.materialize import materialize_mappings, push_to_fuseki
from semantic_platform.r2rdf import MAP

WAREHOUSE_MAPPING = """
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sp: <https://example.org/semantic-platform/core#> .
@prefix map: <https://example.org/semantic-platform/mappings#> .
@prefix gov: <https://example.org/semantic-platform/governance#> .

<https://example.org/mapping/warehouse>
    a rr:TriplesMap, map:Mapping ;
    rdfs:label "External warehouse mapping" ;
    rr:logicalTable [ rr:sqlQuery "SELECT customer_id, customer_name FROM customer" ] ;
    rr:subjectMap [ rr:template "https://example.org/resource/customer/{customer_id}" ;
                    rr:class sp:Entity ; rr:graph <urn:graph:warehouse> ] ;
    rr:predicateObjectMap [ rr:predicate sp:identifier ;
        rr:objectMap [ rr:column "customer_id" ; rr:datatype xsd:string ] ] ;
    rr:predicateObjectMap [ rr:predicate rdfs:label ;
        rr:objectMap [ rr:column "customer_name" ; rr:datatype xsd:string ] ] ;
    map:sourcedFrom <https://example.org/source-dataset/warehouse> ;
    map:targetGraph <urn:graph:warehouse> ;
    map:version "1.0.0" ;
    gov:hasOwner gov:platformOwner ;
    gov:hasSteward gov:platformSteward .
"""


class _FakeJenaHandler(BaseHTTPRequestHandler):
    """Minimal in-memory Fuseki emulator (Graph Store Protocol + SPARQL)."""

    store: dict[str, int] = {}

    def log_message(self, *args):  # silence test server logging
        pass

    def do_GET(self):  # health check (/) and dataset existence (/<dataset>)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_PUT(self):  # graph upload: /<dataset>/data?graph=<uri>
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        graph_uri = parse_qs(urlparse(self.path).query).get("graph", [""])[0]
        graph = Graph()
        graph.parse(data=body, format="turtle")
        type(self).store[graph_uri] = len(graph)
        self.send_response(200)
        self.end_headers()

    def do_POST(self):  # SPARQL query: /<dataset>/query
        length = int(self.headers.get("Content-Length", 0))
        query = parse_qs(self.rfile.read(length).decode()).get("query", [""])[0]
        match = re.search(r"GRAPH <([^>]+)>", query)
        count = type(self).store.get(match.group(1), 0) if match else 0
        payload = json.dumps(
            {"head": {"vars": ["count"]}, "results": {"bindings": [{"count": {"value": str(count)}}]}}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/sparql-results+json")
        self.end_headers()
        self.wfile.write(payload)


def _make_snowflake_like_db(path) -> None:
    """Stand in for an external Snowflake warehouse via a file-backed database."""
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE customer (customer_id TEXT PRIMARY KEY, customer_name TEXT NOT NULL)")
    connection.executemany(
        "INSERT INTO customer VALUES (?, ?)",
        [("C-1", "Northwind"), ("C-2", "Globex"), ("C-3", "Initech")],
    )
    connection.commit()
    connection.close()


def test_end_to_end_external_warehouse_and_jena(tmp_path, monkeypatch):
    # --- Simulated external Snowflake warehouse (reached via a connection URL).
    warehouse_db = tmp_path / "snowflake.db"
    _make_snowflake_like_db(warehouse_db)

    r2rml_dir = tmp_path / "r2rml"
    r2rml_dir.mkdir()
    (r2rml_dir / "warehouse.r2rml").write_text(WAREHOUSE_MAPPING, encoding="utf-8")

    # --- Simulated external Apache Jena (a real local HTTP server).
    _FakeJenaHandler.store = {}
    server = HTTPServer(("127.0.0.1", 0), _FakeJenaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        # The same configuration a user gets by uncommenting the external vars in .env.
        monkeypatch.setenv("SOURCE_DATABASE_URL", f"sqlite:///{warehouse_db}")
        monkeypatch.setenv("FUSEKI_BASE_URL", f"http://127.0.0.1:{port}")
        settings = dataclasses.replace(load_settings(), r2rml_dir=r2rml_dir, output_dir=tmp_path / "out")

        # 1. Materialize from the external warehouse.
        results = materialize_mappings(settings)
        assert len(results) == 1
        result = results[0]
        assert result.record_count == 3
        assert result.target_graph == "urn:graph:warehouse"

        materialized = Graph()
        materialized.parse(result.output_path, format="turtle")
        assert (URIRef("https://example.org/resource/customer/C-1"), None, None) in materialized
        assert (None, RDF.type, MAP.MappingExecution) in materialized

        # 2. Push into external Jena over real HTTP.
        loads = push_to_fuseki(results, settings=settings)
        assert loads and all(load.loaded for load in loads)

        # 3. Read the served triple count back from external Jena over real HTTP.
        served = fuseki_graph_triple_counts([result.target_graph], settings=settings)
        assert served == {"urn:graph:warehouse": result.triple_count}
        assert _FakeJenaHandler.store["urn:graph:warehouse"] == result.triple_count
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
