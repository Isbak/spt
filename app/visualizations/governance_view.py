"""Governance dashboard visualization data service."""

from __future__ import annotations

from semantic_platform.analytics import governance_metrics
from semantic_platform.governance import governance_summary


def governance_dashboard_data() -> dict[str, object]:
    """Return governance records and dashboard metrics."""
    summary = governance_summary()
    return {"summary": summary, "metrics": governance_metrics()}
