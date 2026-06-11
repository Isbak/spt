"""Generic governed advisory and optimization services.

A domain-neutral decision-support capability: given an objective, a set of candidate
options drawn from governed data, and weighted criteria, rank the candidates and emit an
**explainable, provenance-recorded recommendation**. It supports agents that "talk to data",
analyse, optimise, and find patterns. Supplier selection is one example configuration (and the
same capabilities apply to cases such as a field service planner and dispatcher) — expressed
entirely as registry data, never as core logic.

The capability is deliberately **advisory only**, consistent with the platform's non-autonomy
guarantee (ADR-0011, ADR-0013): it produces a ranked recommendation and a rationale for human
review — ``AdvisoryResult.ready`` is always ``False`` and nothing here executes a business
action. Carrying out an approved recommendation remains the job of the governed, approval-gated
:mod:`semantic_platform.execution.executor`, invoked by a human, never by this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, RDFS, XSD

from semantic_platform.config import Settings, load_settings
from semantic_platform.graph import load_graph

ADV = Namespace("https://example.org/semantic-platform/advisory#")

MAXIMIZE = "maximize"
MINIMIZE = "minimize"


@dataclass(frozen=True)
class Criterion:
    """One weighted scoring criterion expressed over a numeric candidate attribute."""

    name: str
    weight: float = 1.0
    direction: str = MAXIMIZE

    def __post_init__(self) -> None:
        if self.direction not in {MAXIMIZE, MINIMIZE}:
            raise ValueError(f"Unsupported criterion direction: {self.direction}")


@dataclass(frozen=True)
class Candidate:
    """A candidate option with numeric attributes used for scoring."""

    uri: str
    label: str
    attributes: Mapping[str, float]


@dataclass(frozen=True)
class RankedCandidate:
    """A scored candidate with a transparent per-criterion contribution breakdown."""

    uri: str
    label: str
    score: float
    breakdown: Mapping[str, float]


@dataclass(frozen=True)
class AdvisoryResult:
    """Outcome of a governed advisory: a ranked, explainable, non-executing recommendation."""

    objective: str
    ranked: tuple[RankedCandidate, ...]
    recommendation: str
    explanation: str
    explanation_iri: str
    provenance: Graph
    ready: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a JSON/template-friendly representation."""
        return {
            "objective": self.objective,
            "recommendation": self.recommendation,
            "explanation": self.explanation,
            "explanation_iri": self.explanation_iri,
            "ready": self.ready,
            "ranked": [
                {
                    "uri": item.uri,
                    "label": item.label,
                    "score": item.score,
                    "breakdown": dict(item.breakdown),
                }
                for item in self.ranked
            ],
        }


def _local_id(uri: URIRef | str) -> str:
    value = str(uri)
    return value.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def score_candidates(
    candidates: Sequence[Candidate], criteria: Sequence[Criterion]
) -> tuple[RankedCandidate, ...]:
    """Rank candidates with a transparent, min-max-normalised weighted sum.

    Each criterion is normalised to ``[0, 1]`` across the candidate set, flipped for
    ``minimize`` criteria, then weighted by its share of the total weight. Ranking is
    deterministic: highest score first, ties broken by URI.
    """
    ranges: dict[str, tuple[float, float]] = {}
    for criterion in criteria:
        values = [
            candidate.attributes[criterion.name]
            for candidate in candidates
            if criterion.name in candidate.attributes
        ]
        if values:
            ranges[criterion.name] = (min(values), max(values))

    total_weight = sum(abs(criterion.weight) for criterion in criteria) or 1.0
    ranked: list[RankedCandidate] = []
    for candidate in candidates:
        breakdown: dict[str, float] = {}
        score = 0.0
        for criterion in criteria:
            value = candidate.attributes.get(criterion.name)
            if value is None or criterion.name not in ranges:
                continue
            low, high = ranges[criterion.name]
            normalised = 0.5 if high == low else (value - low) / (high - low)
            if criterion.direction == MINIMIZE:
                normalised = 1.0 - normalised
            contribution = (criterion.weight / total_weight) * normalised
            breakdown[criterion.name] = round(contribution, 6)
            score += contribution
        ranked.append(RankedCandidate(candidate.uri, candidate.label, round(score, 6), breakdown))
    return tuple(sorted(ranked, key=lambda item: (-item.score, item.uri)))


def candidates_from_graph(
    candidate_type: str | URIRef,
    criteria: Sequence[Criterion],
    *,
    settings: Settings | None = None,
    graph: Graph | None = None,
) -> list[Candidate]:
    """Pull candidate resources of ``candidate_type`` and their numeric criterion attributes.

    Generic over any graph: each criterion ``name`` is matched against the local name of a
    datatype property on the candidate, and numeric literal values are collected as attributes.
    """
    graph = graph if graph is not None else load_graph(settings=settings or load_settings())
    target = URIRef(str(candidate_type))
    wanted = {criterion.name for criterion in criteria}
    candidates: list[Candidate] = []
    for subject in graph.subjects(RDF.type, target):
        if not isinstance(subject, URIRef):
            continue
        attributes: dict[str, float] = {}
        for predicate, value in graph.predicate_objects(subject):
            name = _local_id(predicate)
            if name in wanted and isinstance(value, Literal):
                try:
                    attributes[name] = float(value.toPython())
                except (TypeError, ValueError):
                    continue
        label = graph.value(subject, RDFS.label)
        candidates.append(
            Candidate(
                uri=str(subject),
                label=str(label) if label is not None else _local_id(subject),
                attributes=attributes,
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.uri)


def _build_explanation(
    objective: str, criteria: Sequence[Criterion], ranked: Sequence[RankedCandidate]
) -> str:
    criteria_text = ", ".join(
        f"{criterion.name} (weight {criterion.weight}, {criterion.direction})"
        for criterion in criteria
    )
    if not ranked:
        return (
            f"Objective: {objective}. No candidates were available to evaluate against "
            f"criteria: {criteria_text or 'none'}. Advisory only; human approval required."
        )
    top = ranked[0]
    runner_up = f" ahead of {ranked[1].label} ({ranked[1].score})" if len(ranked) > 1 else ""
    return (
        f"Objective: {objective}. Evaluated {len(ranked)} candidates against criteria: "
        f"{criteria_text or 'none'}. Recommended {top.label} with score {top.score}{runner_up}. "
        "Advisory only; this recommendation requires human approval before any execution."
    )


def _record_provenance(
    objective: str, recommender: str, recommendation: str, candidate_count: int
) -> tuple[Graph, URIRef]:
    graph = Graph()
    graph.bind("prov", PROV)
    graph.bind("adv", ADV)
    now = datetime.now(UTC).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    activity = URIRef(ADV[f"advisory-{stamp}-{candidate_count}"])
    entity = URIRef(ADV[f"advisory-entity-{stamp}-{candidate_count}"])
    agent = URIRef(ADV[recommender])
    graph.add((activity, RDF.type, ADV.AdvisoryActivity))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((agent, RDF.type, PROV.Agent))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    graph.add((activity, ADV.objective, Literal(objective)))
    graph.add((activity, ADV.candidateCount, Literal(candidate_count, datatype=XSD.integer)))
    graph.add((activity, ADV.advisoryOnly, Literal(True, datatype=XSD.boolean)))
    graph.add((activity, PROV.endedAtTime, Literal(now.isoformat(), datatype=XSD.dateTime)))
    graph.add((entity, RDF.type, PROV.Entity))
    graph.add((entity, RDF.type, ADV.Recommendation))
    graph.add((entity, PROV.wasGeneratedBy, activity))
    graph.add((entity, PROV.wasAttributedTo, agent))
    if recommendation:
        graph.add((entity, ADV.recommends, URIRef(recommendation)))
    return graph, activity


def recommend(
    objective: str,
    candidates: Sequence[Candidate],
    criteria: Sequence[Criterion],
    *,
    recommender: str = "advisory-planner",
    settings: Settings | None = None,
) -> AdvisoryResult:
    """Rank candidates against weighted criteria and return a governed, non-executing advisory.

    The result is advisory only: ``ready`` is always ``False`` and a PROV-O record attributes
    the recommendation to ``recommender``. Nothing is executed.
    """
    _ = settings  # accepted for interface symmetry; scoring is pure and graph-independent
    ranked = score_candidates(candidates, criteria)
    recommendation = ranked[0].uri if ranked else ""
    explanation = _build_explanation(objective, criteria, ranked)
    provenance, activity = _record_provenance(
        objective, recommender, recommendation, len(candidates)
    )
    return AdvisoryResult(
        objective=objective,
        ranked=ranked,
        recommendation=recommendation,
        explanation=explanation,
        explanation_iri=str(activity),
        provenance=provenance,
        ready=False,
    )
