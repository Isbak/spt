from rdflib import Graph, Literal, Namespace
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

from app.visualizations.graph_explorer import graph_explorer_data
from semantic_platform.graph_view import build_graph_view, node_detail
from app.visualizations.ontology_browser import ontology_browser_data
from app.visualizations.provenance_view import provenance_view_data
from app.visualizations.reasoning_view import explanations_data, reasoning_dashboard_data
from semantic_platform.analytics import (
    analytics_summary,
    governance_metrics,
    graph_density,
    lineage_depth,
    ontology_statistics,
    provenance_metrics,
)
from semantic_platform.search import search_graph

EX = Namespace("https://example.org/test#")
PROV = Namespace("http://www.w3.org/ns/prov#")
GOV = Namespace("https://example.org/semantic-platform/governance#")


def test_graph_explorer_loads_filters_and_expands():
    data = graph_explorer_data(query="Dataset", limit=10)

    assert data["node_count"] > 0
    assert data["edge_count"] > 0
    assert all(
        "label" in node and "type" in node and "provenance" in node for node in data["nodes"]
    )


def test_build_graph_view_enriches_nodes_and_edges():
    graph = Graph()
    graph.add((EX.alice, RDF.type, EX.Person))
    graph.add((EX.alice, RDFS.label, Literal("Alice")))
    graph.add((EX.bob, RDF.type, EX.Person))
    graph.add((EX.alice, EX.knows, EX.bob))

    view = build_graph_view(graph)

    # alice, bob, and the Person class are all URIRef terms → nodes; the three
    # URIRef↔URIRef triples (two rdf:type, one knows) become edges.
    assert view["node_count"] == 3
    assert view["edge_count"] == 3
    alice = next(n for n in view["nodes"] if n["id"] == str(EX.alice))
    # Preserved contract keys plus the new enrichment fields.
    assert {"id", "label", "type", "group", "provenance", "degree", "title"} <= set(alice)
    assert alice["group"] == "Person"
    assert alice["degree"] == 2
    edge = view["edges"][0]
    assert {"id", "from", "to", "label", "predicate", "title"} <= set(edge)


def test_build_graph_view_filters_by_query_and_focus():
    graph = Graph()
    graph.add((EX.alice, EX.knows, EX.bob))
    graph.add((EX.carol, EX.knows, EX.dave))

    focused = build_graph_view(graph, node=str(EX.alice))
    assert {n["id"] for n in focused["nodes"]} == {str(EX.alice), str(EX.bob)}

    filtered = build_graph_view(graph, query="carol")
    assert {n["id"] for n in filtered["nodes"]} == {str(EX.carol), str(EX.dave)}


def test_node_detail_splits_properties_and_relationships():
    graph = Graph()
    graph.add((EX.alice, RDF.type, EX.Person))
    graph.add((EX.alice, RDFS.label, Literal("Alice")))
    graph.add((EX.alice, RDFS.comment, Literal("An example person.")))
    graph.add((EX.alice, EX.knows, EX.bob))
    graph.add((EX.org, EX.employs, EX.alice))

    detail = node_detail(graph, str(EX.alice))

    assert detail["label"] == "Alice"
    assert str(EX.Person) in detail["types"]
    assert detail["comment"] == "An example person."
    assert detail["outgoing_count"] == 1
    assert detail["incoming_count"] == 1
    assert detail["outgoing"][0]["target"] == str(EX.bob)
    assert detail["incoming"][0]["source"] == str(EX.org)
    # rdfs:label is surfaced as a literal property, not as a relationship.
    assert any(p["value"] == "Alice" for p in detail["properties"])


def test_ontology_browser_renders_hierarchy_properties_instances():
    data = ontology_browser_data()

    assert data["statistics"]["class_count"] > 0
    assert data["statistics"]["property_count"] > 0
    assert data["classes"]
    assert "version" in data


def test_governance_metrics_calculation():
    graph = Graph()
    asset = EX.asset
    graph.add((asset, RDF.type, GOV.GraphAsset))
    graph.add((asset, RDFS.label, Literal("Governed asset")))
    graph.add((asset, GOV.hasOwner, EX.owner))
    graph.add((EX.owner, RDFS.label, Literal("Owner")))

    metrics = governance_metrics(graph=graph)

    assert metrics["asset_count"] == 1
    assert metrics["assets_without_owner"] == 0
    assert metrics["assets_without_steward"] == 1
    assert metrics["ownership_coverage"] == 1.0


def test_provenance_lineage_navigation_metrics():
    graph = Graph()
    graph.add((EX.activity, RDF.type, PROV.Activity))
    graph.add((EX.entity2, PROV.wasDerivedFrom, EX.entity1))
    graph.add((EX.entity3, PROV.wasDerivedFrom, EX.entity2))

    assert lineage_depth(graph, {EX.entity3}) == 3
    assert provenance_metrics(graph)["activity_count"] == 1
    assert provenance_view_data()["metrics"]["lineage_depth"] >= 1


def test_reasoning_dashboard_and_explanations_render():
    dashboard = reasoning_dashboard_data()
    rows = explanations_data()

    assert dashboard["inference_volume"] >= 0
    assert "explanation_coverage" in dashboard
    assert rows
    assert {"assertion", "rule", "source_triples", "confidence", "timestamp"}.issubset(rows[0])


def test_search_label_uri_and_dataset_search():
    graph = Graph()
    graph.add((EX.dataset, RDFS.label, Literal("Customer Dataset")))
    graph.add((EX.dataset, DCTERMS.description, Literal("Dataset for semantic search")))

    label_results = search_graph("Customer", graph=graph)
    uri_results = search_graph("dataset", graph=graph)
    empty_results = search_graph("", graph=graph)

    assert label_results[0].match_type == "Label"
    assert uri_results
    assert empty_results == []


def test_analytics_graph_and_ontology_statistics():
    graph = Graph()
    graph.add((EX.Child, RDF.type, OWL.Class))
    graph.add((EX.Parent, RDF.type, OWL.Class))
    graph.add((EX.Child, RDFS.subClassOf, EX.Parent))
    graph.add((EX.prop, RDF.type, OWL.ObjectProperty))
    graph.add((EX.prop, RDFS.domain, EX.Child))

    stats = ontology_statistics(graph)

    assert graph_density(graph) > 0
    assert stats["class_count"] == 2
    assert stats["property_count"] == 1
    assert stats["hierarchy_depth"] == 2


def test_full_analytics_summary_smoke():
    summary = analytics_summary()

    assert summary.node_count > 0
    assert summary.edge_count > 0
    assert summary.class_count > 0
