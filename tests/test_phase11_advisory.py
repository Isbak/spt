"""Phase 11: generic governed advisory / optimization capability."""

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS

import pytest

from app.app import create_app
from app.visualizations.advisory_view import advisory_dashboard_data, sample_advisory
from semantic_platform.advisory import (
    ADV,
    Candidate,
    Criterion,
    candidates_from_graph,
    recommend,
    score_candidates,
)
from semantic_platform.agents.registry import AgentRegistry, AgentStatus
from semantic_platform.agents.tools import AgentToolRegistry
from semantic_platform.api import advise
from semantic_platform.graph import load_graph
from semantic_platform.validate import validate_shacl

EX = Namespace("https://example.org/test#")

CRITERIA = (
    Criterion("cost", weight=1.0, direction="minimize"),
    Criterion("quality", weight=1.0, direction="maximize"),
)


def _candidates() -> list[Candidate]:
    return [
        Candidate("urn:opt:a", "A", {"cost": 10.0, "quality": 0.5}),
        Candidate("urn:opt:b", "B", {"cost": 5.0, "quality": 0.9}),
    ]


def test_score_candidates_ranks_by_weighted_criteria():
    ranked = score_candidates(_candidates(), CRITERIA)

    assert [item.uri for item in ranked] == ["urn:opt:b", "urn:opt:a"]
    # Each candidate's score equals the sum of its per-criterion contributions.
    for item in ranked:
        assert item.score == pytest.approx(round(sum(item.breakdown.values()), 6))


def test_score_candidates_minimize_direction_flips_normalisation():
    ranked = {item.uri: item for item in score_candidates(_candidates(), CRITERIA)}

    # B is cheapest, so it gets the full cost contribution; A gets zero for cost.
    assert ranked["urn:opt:b"].breakdown["cost"] == pytest.approx(0.5)
    assert ranked["urn:opt:a"].breakdown["cost"] == pytest.approx(0.0)


def test_score_candidates_equal_values_use_neutral_midpoint():
    candidates = [
        Candidate("urn:opt:a", "A", {"cost": 7.0}),
        Candidate("urn:opt:b", "B", {"cost": 7.0}),
    ]
    ranked = score_candidates(candidates, [Criterion("cost")])

    assert all(item.breakdown["cost"] == pytest.approx(0.5) for item in ranked)


def test_recommend_is_advisory_only_and_records_provenance():
    result = recommend("Pick the best option", _candidates(), CRITERIA)

    assert result.ready is False
    assert result.recommendation == "urn:opt:b"
    assert "human approval" in result.explanation.lower()
    assert result.explanation_iri.startswith(str(ADV))
    assert len(result.provenance) > 0
    payload = result.as_dict()
    assert payload["ready"] is False
    assert payload["ranked"][0]["uri"] == "urn:opt:b"


def test_recommend_handles_no_candidates():
    result = recommend("Nothing to rank", [], CRITERIA)

    assert result.ranked == ()
    assert result.recommendation == ""
    assert "no candidates" in result.explanation.lower()


def test_criterion_rejects_unsupported_direction():
    with pytest.raises(ValueError):
        Criterion("cost", direction="sideways")


def test_candidates_from_graph_extracts_numeric_attributes():
    graph = Graph()
    graph.add((EX.a, RDF.type, EX.Option))
    graph.add((EX.a, EX.cost, Literal(10)))
    graph.add((EX.a, EX.quality, Literal(0.9)))
    graph.add((EX.a, RDFS.label, Literal("A")))
    graph.add((EX.a, EX.note, Literal("ignored-non-criterion")))
    graph.add((EX.b, RDF.type, EX.Option))
    graph.add((EX.b, EX.cost, Literal(5)))
    graph.add((EX.b, EX.quality, Literal("n/a")))  # non-numeric wanted value is skipped

    candidates = candidates_from_graph(EX.Option, CRITERIA, graph=graph)

    assert [item.uri for item in candidates] == [str(EX.a), str(EX.b)]
    assert candidates[0].label == "A"
    assert candidates[1].label == "b"  # falls back to the local id when no label
    assert candidates[0].attributes == {"cost": 10.0, "quality": 0.9}
    assert candidates[1].attributes == {"cost": 5.0}


def test_advise_facade_ranks_graph_candidates():
    # The example advisory registry exposes adv:Criterion individuals with numeric weights.
    result = advise(
        "Rank criteria by weight",
        ADV.Criterion,
        [Criterion("criterionWeight", direction="maximize")],
    )

    assert result.ready is False
    assert len(result.ranked) >= 1
    # The skill-match criterion carries the highest weight (3.0) in the example registry.
    assert result.recommendation.endswith("criterion-skill-match")


def test_advisory_tool_enforces_read_permission():
    tools = AgentToolRegistry(graph=load_graph())
    registry = AgentRegistry()
    dispatcher = registry.require("field-service-dispatcher")

    result = tools.execute(
        dispatcher,
        "advisory",
        objective="Rank example criteria",
        candidate_type=str(ADV.Criterion),
        criteria=[{"name": "criterionWeight", "direction": "maximize"}],
    )
    assert result["ready"] is False
    assert result["ranked"]

    # An agent without the advisory tool assignment is denied.
    context_agent = registry.require("semantic-context-agent")
    with pytest.raises(PermissionError):
        tools.execute(
            context_agent,
            "advisory",
            objective="x",
            candidate_type=str(ADV.Criterion),
            criteria=[],
        )


def test_example_planner_and_dispatcher_are_registered():
    registry = AgentRegistry()

    assert not registry.validate()
    for agent_id in ("field-service-planner", "field-service-dispatcher"):
        agent = registry.require(agent_id)
        assert agent.status == AgentStatus.APPROVED
        assert "advisory" in agent.allowed_tools
        assert agent.permissions.can_read("reference")


def test_advisory_assets_conform_to_shacl():
    assert validate_shacl().conforms


def test_advisory_dashboard_sample():
    data = advisory_dashboard_data()

    assert data["ready"] is False
    assert len(data["ranked"]) == 3
    assert sample_advisory().recommendation


def test_advisory_flask_routes():
    app = create_app()
    client = app.test_client()

    assert client.get("/advisory").status_code == 200
    assert client.post("/api/advisory", json={}).status_code == 200

    typed = client.post(
        "/api/advisory",
        json={
            "objective": "Rank criteria",
            "candidate_type": str(ADV.Criterion),
            "criteria": [{"name": "criterionWeight", "direction": "maximize"}],
        },
    )
    assert typed.status_code == 200
    assert typed.get_json()["ready"] is False

    governed = client.post(
        "/api/advisory",
        json={
            "agent_id": "field-service-dispatcher",
            "candidate_type": str(ADV.Criterion),
            "criteria": [{"name": "criterionWeight", "direction": "maximize"}],
        },
    )
    assert governed.status_code == 200

    denied = client.post("/api/advisory", json={"agent_id": "semantic-context-agent"})
    assert denied.status_code == 403

    missing = client.post("/api/advisory", json={"agent_id": "no-such-agent"})
    assert missing.status_code == 404
