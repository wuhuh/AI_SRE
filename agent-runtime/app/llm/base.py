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
    # native function calling：assistant 消息回传模型发起的 tool_calls，
    # tool 消息通过 tool_call_id 与之一一对应。
    tool_calls: list[dict[str, Any]] | None = None


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
