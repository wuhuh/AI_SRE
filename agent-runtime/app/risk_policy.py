"""Static risk policy.

Risk is defined explicitly by action names, not by LLM judgment. The AI can only
recommend actions; this policy decides whether human approval is required.
"""
from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    HIGH_RISK = "HIGH_RISK"


ACTION_RISK = {
    "restart_pod": RiskLevel.LOW_RISK,
    "scale_deployment": RiskLevel.HIGH_RISK,
    "delete_pod": RiskLevel.HIGH_RISK,
    "clear_redis_cache": RiskLevel.LOW_RISK,
    "increase_redis_maxclients": RiskLevel.HIGH_RISK,
    "increase_db_pool_size": RiskLevel.HIGH_RISK,
    "disable_fault": RiskLevel.LOW_RISK,
    "rollback_deployment": RiskLevel.HIGH_RISK,
    "restart_service": RiskLevel.LOW_RISK,
}


def classify(action: str | None) -> RiskLevel:
    if not action:
        return RiskLevel.HIGH_RISK
    return ACTION_RISK.get(action.strip().lower(), RiskLevel.LOW_RISK)


def requires_approval(action: str | None) -> bool:
    return classify(action) == RiskLevel.HIGH_RISK