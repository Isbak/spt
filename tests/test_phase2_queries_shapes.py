from semantic_platform.config import load_settings
from semantic_platform.graph import load_graph
from semantic_platform.query import read_query, result_rows
from semantic_platform.validate import run_validation


def test_new_sparql_queries_return_results():
    settings = load_settings()
    graph = load_graph(settings=settings)
    for query_name in [
        "governance_summary.rq",
        "provenance_trace.rq",
        "named_graphs.rq",
        "ontology_version.rq",
    ]:
        rows = result_rows(graph.query(read_query(settings.queries_dir / query_name)))
        assert rows, query_name


def test_new_shacl_shapes_pass():
    _, shacl_report = run_validation()
    assert shacl_report.conforms
