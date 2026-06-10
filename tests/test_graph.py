from semantic_platform.graph import graph_stats, load_graph


def test_load_graph_reads_phase1_assets():
    graph = load_graph()
    assert len(graph) > 0
    assert (None, None, None) in graph


def test_graph_stats_counts_loaded_graph():
    stats = graph_stats(load_graph())
    assert stats.triples > 0
    assert stats.subjects > 0
    assert stats.predicates > 0
    assert stats.objects > 0
