from __future__ import annotations

import json
from typing import Any

from app.llm.base import LLMProvider, Message
from app.models import LLMResult


class MockLLMProvider(LLMProvider):
    """Deterministic mock used by tests and local demos.

    It returns valid structured JSON for planning, diagnosis and verification.
    """

    def __init__(self, mode: str = "normal"):
        self.mode = mode

    def complete(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> LLMResult:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        if self.mode == "invalid_json":
            return LLMResult("not json at all", input_tokens=10, output_tokens=5)
        if self.mode == "unknown_tool":
            return LLMResult(json.dumps({
                "thought": "I need data",
                "tool": "not_exist",
                "arguments": {}
            }), input_tokens=10, output_tokens=10)
        lowered = last_user.lower()
        if "verification data" in lowered or "return json {\"status\"" in lowered:
            return LLMResult(json.dumps({
                "status": "RECOVERED",
                "detail": "error_rate dropped and latency returned to baseline"
            }), input_tokens=50, output_tokens=20)
        if "diagnos" in lowered or "root cause" in lowered or "rootcause" in lowered:
            return LLMResult(json.dumps({
                "rootCause": "redis_connection_pool_exhausted",
                "confidence": 0.91,
                "evidence": [
                    {"source": "prometheus", "key": "redis_connection_usage_high", "content": "used_connections==maxclients"},
                    {"source": "logs", "key": "redis_timeout_log", "content": "RedisConnectionFailureException: pool exhausted"},
                    {"source": "trace", "key": "redis_span_latency_high", "content": "redis SET p99=3.2s"}
                ],
                "recommendedActions": ["restart_pod", "scale_deployment"]
            }), input_tokens=120, output_tokens=80)
        # Plan output
        plan = ["query_prometheus", "query_logs", "query_trace", "retrieve_runbook"]
        return LLMResult(json.dumps({"plan": plan}), input_tokens=30, output_tokens=15)
