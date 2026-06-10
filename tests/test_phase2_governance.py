from rdflib import Graph, Namespace
from rdflib.namespace import RDF

from semantic_platform.governance import GOV, governance_summary, load_governance_metadata, validate_graph_governance


def test_governance_metadata_loading():
    graph = load_governance_metadata()
    assert (None, RDF.type, GOV.GraphAsset) in graph
    assert governance_summary()["graph_asset_count"] >= 8


def test_graph_ownership_validation_reports_missing_metadata():
    graph = Graph()
    asset = Namespace("urn:test:")["graph"]
    graph.add((asset, RDF.type, GOV.GraphAsset))
    errors = validate_graph_governance(graph=graph)
    assert any("owner" in error for error in errors)
    assert any("steward" in error for error in errors)
    assert any("classification" in error for error in errors)
