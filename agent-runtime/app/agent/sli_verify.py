"""P1-AR-06: 确定性 SLI 验证——修复后状态由指标判定，LLM 只写解释。

判定规则（文档《独立修订版》11.3/11.4 三态语义）：
  error_rate <= 上限 且 p95 <= 上限 且流量样本充足 → RECOVERED
  明确超标 → NOT_RECOVERED
  无数据 / NaN / Inf / 负值 / 零流量 / 样本不足 / 配置非法 → UNKNOWN

关键边界：**零流量不能当成健康证据**。error_rate=0 只在「总流量有效」时
才能当作无错误；没有请求（分母为零）或采集失败（分子分母都缺）不能判恢复。
"""
from __future__ import annotations

import json
import math
import os


def observation_window_seconds() -> float:
    return float(os.getenv("VERIFICATION_OBSERV_WINDOW_SECONDS", "60"))


def max_error_rate() -> float:
    return float(os.getenv("VERIFICATION_MAX_ERROR_RATE", "0.01"))


def max_p95_seconds() -> float:
    return float(os.getenv("VERIFICATION_MAX_P95_SECONDS", "1.0"))


def min_requests() -> int:
    """恢复判定的最小有效请求样本数（文档 11.4 教学配置 = 100，非生产阈值）。"""
    return int(os.getenv("VERIFICATION_MIN_REQUESTS", "100"))


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


def _is_valid_metric(value) -> bool:
    """有效指标：有限数值且非负。NaN/Inf/负值都不能参与判定（文档 11.5）。"""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value >= 0


def judge(error_rate, p95, requests=None, *,
          max_error: float | None = None,
          max_p95: float | None = None,
          min_req: int | None = None) -> str:
    """返回 RECOVERED / NOT_RECOVERED / UNKNOWN。

    requests：观察窗内有效请求总数（可为 None = 流量未知，跳过流量检查；
    但调用方在流量未知时也不应把空错误序列默认成 0——见 verification._measure_sli）。
    """
    max_err = max_error_rate() if max_error is None else max_error
    max_p = max_p95_seconds() if max_p95 is None else max_p95
    min_r = min_requests() if min_req is None else min_req

    # 文档 11.4：阈值配置非法直接报错——错误配置比 UNKNOWN 更危险
    if not math.isfinite(max_err) or not 0 <= max_err <= 1:
        raise ValueError("invalid max_error_rate")
    if not math.isfinite(max_p) or max_p < 0:
        raise ValueError("invalid max_p95_seconds")
    if not isinstance(min_r, int) or min_r <= 0:
        raise ValueError("min_requests must be a positive integer")

    # 无数据 → UNKNOWN（不是健康也不是故障）
    if not _is_valid_metric(error_rate) or not _is_valid_metric(p95):
        return "UNKNOWN"

    # 流量样本检查：给了 requests 才判定；零流量 / 样本不足 → UNKNOWN
    if requests is not None:
        if not _is_valid_metric(requests) or requests < min_r:
            return "UNKNOWN"

    if error_rate <= max_err and p95 <= max_p:
        return "RECOVERED"
    return "NOT_RECOVERED"
