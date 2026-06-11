"""Risk classification for governed execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(frozen=True)
class RiskDecision:
    level: RiskLevel
    approvals_required: int
    restricted: bool
    audit_required: bool


class RiskClassifier:
    """Map action semantics to governance requirements."""

    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

    def classify(self, action_type: str, target_type: str = "REST API", declared: str | None = None) -> RiskDecision:
        level = RiskLevel(declared) if declared else self._infer(action_type, target_type)
        approvals = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }[level]
        return RiskDecision(level, approvals, level in {RiskLevel.HIGH, RiskLevel.CRITICAL}, level != RiskLevel.LOW)

    def allowed_at_or_below(self, level: RiskLevel, threshold: RiskLevel) -> bool:
        return self.order.index(level) <= self.order.index(threshold)

    def _infer(self, action_type: str, target_type: str) -> RiskLevel:
        action = action_type.lower()
        target = target_type.lower()
        if "delete" in action or "stop" in action or "database" in target:
            return RiskLevel.HIGH
        if "update" in action or "file" in target:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
