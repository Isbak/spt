"""Governance dashboard visualization data service."""

from __future__ import annotations

from semantic_platform.analytics import governance_metrics
from semantic_platform.config import Settings
from semantic_platform.governance import governance_summary


def governance_dashboard_data(settings: Settings | None = None) -> dict[str, object]:
    """Return governance records and dashboard metrics for the given context."""
    summary = governance_summary(settings=settings)
    return {"summary": summary, "metrics": governance_metrics(settings=settings)}
