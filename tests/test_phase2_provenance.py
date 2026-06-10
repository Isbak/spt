from datetime import UTC, datetime

from rdflib import URIRef

from semantic_platform.provenance import PROV, create_provenance_record, provenance_chain, serialize_provenance


def test_provenance_record_creation_and_serialization():
    activity = create_provenance_record(
        "Graph load activity",
        "urn:agent:test",
        entity="urn:graph:test",
        started_at=datetime(2026, 6, 10, tzinfo=UTC),
    )
    graph = serialize_provenance(activity)
    assert (URIRef(activity.activity), PROV.wasAssociatedWith, URIRef("urn:agent:test")) in graph
    assert (URIRef("urn:graph:test"), PROV.wasGeneratedBy, URIRef(activity.activity)) in graph


def test_provenance_querying():
    activity = create_provenance_record(
        "RDF validation activity",
        "urn:agent:test",
        entity="urn:dataset:test",
        started_at=datetime(2026, 6, 10, tzinfo=UTC),
    )
    graph = serialize_provenance(activity)
    rows = provenance_chain("urn:dataset:test", graph=graph)
    assert rows[0]["activity"] == activity.activity
    assert rows[0]["agent"] == "urn:agent:test"
