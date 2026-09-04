from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.llm.base import LLMProvider, Message
from app.models import LLMResult


class OpenAICompatibleLLMProvider(LLMProvider):
    """Minimal OpenAI-compatible chat completions provider.

    It uses the `OPENAI_BASE_URL`, `OPENAI_API_KEY` and `OPENAI_MODEL`
    environment variables. No vendor SDK is required.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 model: str | None = None, timeout_seconds: float = 15.0):
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout_seconds = timeout_seconds

    def complete(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if tools:
            payload["tools"] = tools
        headers = {"Authorization": f"Bearer {self.api_key}"}
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        return LLMResult(
            content=choice.get("content") or "",
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            tool_calls=choice.get("tool_calls") or [],
        )