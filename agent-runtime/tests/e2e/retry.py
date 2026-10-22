"""E2E 级瞬时失败重试。

只重试环境抖动：连接 reset/超时、0-token LLM、可恢复的解析失败。
错误根因、验证 UNKNOWN、HTTP 400/500、断言失败都不重试。
"""
from __future__ import annotations

import functools
import os
import time
import urllib.error

RETRYABLE_HTTP_CODES = frozenset({408, 429, 502, 503, 504})
TRANSIENT_REASON_CODES = frozenset({"llm_error", "invalid_json"})


class TransientE2EError(RuntimeError):
    """测试 helper 显式标记的可重试失败；AssertionError 不属于此类。"""


def is_transient_diagnosis(body: dict) -> bool:
    """判断一次 Agent 诊断响应是否只是“没跑成”，而不是模型主动拒答。"""
    diag = body.get("diagnosis") or {}
    if not diag:
        return True
    tokens = int(diag.get("llm_input_tokens") or 0)
    status = (diag.get("status") or "").upper()
    reason = (diag.get("reason_code") or "").lower()
    if status == "TIMEOUT":
        return True
    if status == "UNKNOWN" and reason in TRANSIENT_REASON_CODES:
        return True
    # 0 token 只在「没有给出结论」时视为 provider 未真正返回；
    # 契约 mock / 旧版本可能不带 token 字段，但有有效 root_cause 时不应重试。
    answered = str(diag.get("root_cause") or "").strip().lower()
    return tokens == 0 and status == "UNKNOWN" and answered in ("", "unknown")


def is_retryable_exception(exc: Exception) -> bool:
    """HTTPError 是 URLError 子类，必须先判断 code，避免 400 被误重试。"""
    if isinstance(exc, TransientE2EError):
        return True
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in RETRYABLE_HTTP_CODES
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionResetError))


def retry_transient(fn):
    """测试方法级重试装饰器。

    - E2E_RETRIES 默认 0（本地不复跑）；
    - 每次 attempt 前设置 self._attempt，供唯一 alert resource 使用；
    - 重试前调用 self._reset_faults()，避免上一轮故障残留。
    """
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        max_attempts = max(1, int(os.getenv("E2E_RETRIES", "0")) + 1)
        base_delay = float(os.getenv("E2E_RETRY_DELAY_SECONDS", "5"))
        max_delay = float(os.getenv("E2E_RETRY_MAX_DELAY_SECONDS", "30"))
        for attempt in range(1, max_attempts + 1):
            self._attempt = attempt
            try:
                return fn(self, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - 只对白名单异常重试
                if not is_retryable_exception(exc) or attempt >= max_attempts:
                    raise
                delay = max(0.0, min(max_delay, base_delay * (2 ** (attempt - 1))))
                print(f"[E2E][retry] attempt {attempt}/{max_attempts} transient: {exc}; "
                      f"sleep {delay:.1f}s", flush=True)
                try:
                    self._reset_faults()
                except Exception:
                    pass
                time.sleep(delay)
    return wrapper
