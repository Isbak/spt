from semantic_platform.named_graphs import graph_lifecycle_summary, list_named_graphs, load_named_graph_manifest, validate_named_graph_metadata


def test_named_graph_manifest_loading():
    graph = load_named_graph_manifest()
    records = list_named_graphs(graph=graph)
    assert len(records) == 8
    assert {record.graph for record in records} >= {"urn:graph:ontology", "urn:graph:provenance"}


def test_named_graph_validation():
    summary = graph_lifecycle_summary()
    assert summary["named_graph_count"] == 8
    assert validate_named_graph_metadata() == []
