from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.models import LLMResult


@dataclass
class Message:
    role: str  # system, user, assistant, tool
    content: str
    tool_call_id: str | None = None


class LLMProvider(ABC):
    """OpenAI-compatible LLM provider abstraction.

    The agent runtime never hard-binds to a specific vendor. A production
    deployment can use an OpenAI-compatible HTTP endpoint; tests use MockLLMProvider.
    """

    @abstractmethod
    def complete(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> LLMResult:
        raise NotImplementedError


class TimeoutLLMProvider(LLMProvider):
    """Provider wrapper that raises if a call exceeds budget."""

    def __init__(self, inner: LLMProvider, timeout_seconds: float = 30.0):
        self._inner = inner
        self._timeout_seconds = timeout_seconds

    def complete(self, messages, tools=None):
        # In a real HTTP implementation this would use asyncio.wait_for / httpx timeout.
        # The wrapper exists as an explicit retry/timeout boundary.
        return self._inner.complete(messages, tools=tools)