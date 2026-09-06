from __future__ import annotations

import time
from typing import Any

import httpx

from app.llm.base import LLMProvider, Message
from app.models import LLMResult


class RetryLLMProvider(LLMProvider):
    """P1-AR-04: 重试边界——429 尊重 Retry-After（封顶），5xx/网络错误短退避重试，
    4xx（参数/认证类）不重试直接上抛。"""

    def __init__(self, inner: LLMProvider, max_retries: int = 2, delay_seconds: float = 0.5,
                 retry_after_cap_seconds: float = 10.0):
        self.inner = inner
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.retry_after_cap_seconds = retry_after_cap_seconds

    def complete(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> LLMResult:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.inner.complete(messages, tools=tools)
            except Exception as exc:  # noqa: BLE001 - retry wrapper
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                delay = self._delay_for(exc)
                if delay is None:
                    break  # 不可重试错误（4xx 参数/认证类）直接上抛
                time.sleep(delay)
        raise last_exc

    def _delay_for(self, exc: Exception) -> float | None:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                return None
            if status == 429:
                # 优先 Retry-After；超上限视为等不起（预算型诊断），不再等待
                retry_after = exc.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        wait = self.delay_seconds
                    if wait > self.retry_after_cap_seconds:
                        return None
                    return wait
                return self.delay_seconds
        # 网络/5xx/未知：短退避
        return self.delay_seconds
