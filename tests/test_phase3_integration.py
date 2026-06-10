from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from app.app import create_app
from semantic_platform.config import load_settings
from semantic_platform.graph import load_graph
from semantic_platform.import_csv import import_csv_file, read_csv
from semantic_platform.import_sql import import_sql_source, load_sqlite_database, query_rows
from semantic_platform.mappings import list_mappings, validate_catalog
from semantic_platform.query import read_query, result_rows
from semantic_platform.r2rdf import MAP, RR, execute_mapping_workflow, load_r2rml_mapping, validate_mapping
from semantic_platform.source_catalog import (
    list_source_datasets,
    register_dataset,
    register_mapping_ownership,
    register_source_system,
)
from semantic_platform.validate import run_validation


def test_r2rml_mapping_parsing_and_validation():
    graph = load_r2rml_mapping("mappings/r2rml/example_person.ttl")
    assert (None, RDF.type, RR.TriplesMap) in graph
    result = validate_mapping(graph)
    assert result.valid, result.errors
    assert not validate_catalog()


def test_r2rml_workflow_generates_rdf_and_provenance():
    rows = read_csv("mappings/csv/people.csv")
    result = execute_mapping_workflow("mappings/r2rml/example_person.ttl", rows)
    assert result.triple_count > 0
    assert (result.execution_iri, RDF.type, MAP.MappingExecution) in result.graph
    assert (URIRef("https://example.org/resource/person/PER-100"), None, None) in result.graph


def test_csv_import_generates_rdf_and_provenance():
    graph = import_csv_file("mappings/csv/people.csv")
    assert (URIRef("https://example.org/resource/person/PER-100"), None, None) in graph
    assert (None, RDF.type, MAP.MappingExecution) in graph


def test_sql_import_generates_rdf_and_provenance():
    graph = import_sql_source("mappings/sql/schema.sql", "mappings/sql/sample_data.sql")
    assert (URIRef("https://example.org/resource/dataset/DS-001"), None, None) in graph
    assert (None, RDF.type, MAP.MappingExecution) in graph


def test_sql_source_rows_are_readable():
    connection = load_sqlite_database("mappings/sql/schema.sql", "mappings/sql/sample_data.sql")
    try:
        rows = query_rows(connection, "SELECT * FROM person ORDER BY person_id")
    finally:
        connection.close()
    assert rows[0]["person_id"] == "PER-001"


def test_source_catalog_registration_and_queries():
    graph = Graph()
    system = register_source_system(graph, "https://example.org/source-system/test", "Test system")
    dataset = register_dataset(
        graph,
        "https://example.org/source-dataset/test",
        "Test dataset",
        system,
        version="1.0",
    )
    register_mapping_ownership(graph, URIRef("https://example.org/mapping/test"))
    assert (system, RDF.type, MAP.SourceSystem) in graph
    assert (dataset, RDF.type, MAP.SourceDataset) in graph
    assert list_source_datasets()


def test_phase3_sparql_queries_return_results():
    settings = load_settings()
    graph = load_graph(settings=settings)
    for query_name in [
        "mappings.rq",
        "source_catalog.rq",
        "mapping_lineage.rq",
        "integration_graphs.rq",
    ]:
        rows = result_rows(graph.query(read_query(settings.queries_dir / query_name)))
        assert rows, query_name


def test_mapping_shapes_pass():
    _, shacl_report = run_validation()
    assert shacl_report.conforms


def test_mapping_catalog_records():
    records = list_mappings()
    assert any(record.label == "Person R2RML mapping" for record in records)
    assert any(record.target_graph == "urn:graph:masterdata" for record in records)


def test_flask_phase3_views_load():
    app = create_app()
    client = app.test_client()
    for path in ["/mappings", "/source-catalog", "/integration", "/mapping-lineage"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert b"Semantic Platform" in response.data
