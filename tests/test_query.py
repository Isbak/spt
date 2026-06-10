from semantic_platform.query import execute_default_query


def test_default_sparql_query_returns_summary_metrics():
    rows = execute_default_query()
    metrics = {row["metric"]: row["value"] for row in rows}
    assert int(metrics["entities"]) >= 1
    assert int(metrics["datasets"]) >= 1
    assert int(metrics["provenance_activities"]) >= 1
