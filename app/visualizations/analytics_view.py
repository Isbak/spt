"""Analytics dashboard visualization data service."""

from __future__ import annotations

from semantic_platform.analytics import analytics_summary
from semantic_platform.config import Settings


def analytics_dashboard_data(settings: Settings | None = None) -> dict[str, int | float]:
    """Return analytics metrics for the dashboard (over the given context's graph)."""
    return analytics_summary(settings=settings).as_dict()
