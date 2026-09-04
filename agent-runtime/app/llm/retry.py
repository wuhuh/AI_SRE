from __future__ import annotations

import time
from typing import Any

from app.llm.base import LLMProvider, Message
from app.models import LLMResult


class RetryLLMProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, max_retries: int = 2, delay_seconds: float = 0.01):
        self.inner = inner
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds

    def complete(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> LLMResult:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.inner.complete(messages, tools=tools)
            except Exception as exc:  # noqa: BLE001 - retry wrapper
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.delay_seconds)
        raise last_exc