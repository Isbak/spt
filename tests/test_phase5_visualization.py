from rdflib import Graph, Literal, Namespace
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

from app.visualizations.graph_explorer import graph_explorer_data
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
