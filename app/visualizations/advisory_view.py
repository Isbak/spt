"""Advisory dashboard visualization data service.

Builds an illustrative, domain-neutral advisory (supplier selection is used as a relatable
example) so the dashboard renders without requiring domain-specific instance data.
"""

from __future__ import annotations

from semantic_platform.advisory import AdvisoryResult, Candidate, Criterion, recommend

SAMPLE_CRITERIA = (
    Criterion("price", weight=2.0, direction="minimize"),
    Criterion("qualityRating", weight=3.0, direction="maximize"),
    Criterion("reliability", weight=1.0, direction="maximize"),
)

SAMPLE_CANDIDATES = (
    Candidate(
        "urn:example:bid:supplier-a",
        "Supplier A",
        {"price": 8.0, "qualityRating": 0.9, "reliability": 1.0},
    ),
    Candidate(
        "urn:example:bid:supplier-b",
        "Supplier B",
        {"price": 3.0, "qualityRating": 0.6, "reliability": 1.0},
    ),
    Candidate(
        "urn:example:bid:supplier-c",
        "Supplier C",
        {"price": 5.0, "qualityRating": 0.8, "reliability": 0.5},
    ),
)


def sample_advisory() -> AdvisoryResult:
    """Return an illustrative governed advisory over example candidate options."""
    return recommend(
        "Recommend the best supplier bid for the contract",
        list(SAMPLE_CANDIDATES),
        list(SAMPLE_CRITERIA),
    )


def advisory_dashboard_data() -> dict[str, object]:
    """Return advisory data for the dashboard."""
    return sample_advisory().as_dict()
