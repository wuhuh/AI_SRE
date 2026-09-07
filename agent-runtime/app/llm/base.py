from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


# P2-CP-22: TimeoutLLMProvider 已删——假超时包装（只透传）。超时由
# OpenAICompatibleLLMProvider 的 httpx timeout 与 RetryLLMProvider 边界负责。
