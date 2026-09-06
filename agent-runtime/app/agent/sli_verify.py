"""P1-AR-06: 确定性 SLI 验证——修复后状态由指标判定，LLM 只写解释。

判定规则：error_rate <= 上限 且 p95 <= 上限 → RECOVERED；
Prometheus 不可达/无数据 → UNKNOWN（交由 LLM 兜底，绝不能凭 LLM 单方说 RECOVERED）。
"""
from __future__ import annotations

import json
import os


def observation_window_seconds() -> float:
    return float(os.getenv("VERIFICATION_OBSERV_WINDOW_SECONDS", "60"))


def max_error_rate() -> float:
    return float(os.getenv("VERIFICATION_MAX_ERROR_RATE", "0.01"))


def max_p95_seconds() -> float:
    return float(os.getenv("VERIFICATION_MAX_P95_SECONDS", "1.0"))


def parse_instant_value(raw: str | None) -> float | None:
    """解析 Prometheus instant query 响应（tool-server 透传 JSON）。"""
    if not raw:
        return None
    try:
        data = json.loads(raw)
        result = data.get("data", {}).get("result") or []
        value = result[0].get("value")
        return float(value[1]) if value else None
    except Exception:  # noqa: BLE001 - 非 JSON/空结果都算无数据
        return None


def judge(error_rate: float | None, p95: float | None) -> str:
    """返回 RECOVERED / NOT_RECOVERED / UNKNOWN。"""
    if error_rate is None or p95 is None:
        return "UNKNOWN"
    if error_rate <= max_error_rate() and p95 <= max_p95_seconds():
        return "RECOVERED"
    return "NOT_RECOVERED"
