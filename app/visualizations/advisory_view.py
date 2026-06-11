"""Advisory dashboard visualization data service.

Builds an illustrative, domain-neutral advisory (a field-service assignment is used only as a
relatable example) so the dashboard renders without requiring domain-specific instance data.
"""

from __future__ import annotations

from semantic_platform.advisory import AdvisoryResult, Candidate, Criterion, recommend

SAMPLE_CRITERIA = (
    Criterion("proximity", weight=2.0, direction="minimize"),
    Criterion("skillMatch", weight=3.0, direction="maximize"),
    Criterion("availability", weight=1.0, direction="maximize"),
)

SAMPLE_CANDIDATES = (
    Candidate(
        "urn:example:assignment:option-a",
        "Option A → Job 17",
        {"proximity": 8.0, "skillMatch": 0.9, "availability": 1.0},
    ),
    Candidate(
        "urn:example:assignment:option-b",
        "Option B → Job 17",
        {"proximity": 3.0, "skillMatch": 0.6, "availability": 1.0},
    ),
    Candidate(
        "urn:example:assignment:option-c",
        "Option C → Job 17",
        {"proximity": 5.0, "skillMatch": 0.8, "availability": 0.5},
    ),
)


def sample_advisory() -> AdvisoryResult:
    """Return an illustrative governed advisory over example candidate options."""
    return recommend(
        "Recommend the best assignment for job 17",
        list(SAMPLE_CANDIDATES),
        list(SAMPLE_CRITERIA),
    )


def advisory_dashboard_data() -> dict[str, object]:
    """Return advisory data for the dashboard."""
    return sample_advisory().as_dict()
