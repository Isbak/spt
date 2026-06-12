from semantic_platform.named_graphs import graph_lifecycle_summary, list_named_graphs, load_named_graph_manifest, validate_named_graph_metadata


def test_named_graph_manifest_loading():
    graph = load_named_graph_manifest()
    records = list_named_graphs(graph=graph)
    assert len(records) == 12
    assert {record.graph for record in records} >= {"urn:graph:ontology", "urn:graph:provenance", "urn:graph:reasoning", "urn:graph:inferred", "urn:graph:validation", "urn:graph:agents"}


def test_named_graph_validation():
    summary = graph_lifecycle_summary()
    assert summary["named_graph_count"] == 12
    assert validate_named_graph_metadata() == []


def test_named_graphs_declare_storage_role():
    """Every manifest graph must declare a valid storage role (ADR-0017)."""
    records = list_named_graphs()
    by_graph = {record.graph: record.stored_in_dataset for record in records}
    assert by_graph["urn:graph:ontology"] == "system"
    assert by_graph["urn:graph:provenance"] == "agents"
    assert by_graph["urn:graph:integration"] == "business"
    assert all(role in {"system", "agents", "business"} for role in by_graph.values())
