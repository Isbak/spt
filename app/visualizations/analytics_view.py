"""Analytics dashboard visualization data service."""

from __future__ import annotations

from semantic_platform.analytics import analytics_summary


def analytics_dashboard_data() -> dict[str, int | float]:
    """Return analytics metrics for the dashboard."""
    return analytics_summary().as_dict()
