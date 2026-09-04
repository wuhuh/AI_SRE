from __future__ import annotations

import json

from app.context import build_context
from app.llm.base import LLMProvider, Message
from app.models import AgentState, Evidence, VerificationResult
from app.tools.registry import ToolRegistry


class VerificationAgent:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, max_steps: int = 6,
                 max_duration_seconds: float = 12.0):
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.max_duration_seconds = max_duration_seconds

    def run(self, state: AgentState) -> VerificationResult:
        import time
        start_time = time.monotonic()
        checks = ["query_prometheus", "query_logs", "query_trace"]
        for tool_name in checks:
            if state.step >= self.max_steps:
                break
            if time.monotonic() - start_time > self.max_duration_seconds:
                break
            call = self.registry.call(tool_name, self._args(tool_name))
            state.tool_calls.append(call)
            state.tool_results[tool_name] = call.result_summary or call.error or ""
            state.step += 1
            if call.status == "SUCCESS":
                state.evidence.append(Evidence(
                    source=tool_name,
                    key=f"verify:{tool_name}",
                    content=call.result_summary[:500],
                ))

        context = build_context(state, state.alert)
        prompt = (
            "Based on verification data, determine if the incident is recovered. "
            'Return JSON {"status": "RECOVERED|NOT_RECOVERED|UNKNOWN", "detail": "..."}\n\n'
            + context.summary
        )
        try:
            result = self.llm.complete([Message(role="user", content=prompt)])
            data = json.loads(result.content)
        except Exception:
            data = {"status": "UNKNOWN", "detail": "LLM verification failed"}
        status = data.get("status", "UNKNOWN")
        if status not in ("RECOVERED", "NOT_RECOVERED", "UNKNOWN"):
            status = "UNKNOWN"
        verification = VerificationResult(status=status, detail=data.get("detail", ""), evidence=state.evidence)
        state.verification = verification
        state.status = "VERIFIED"
        return verification

    def _args(self, tool_name: str) -> dict:
        if tool_name == "query_logs":
            return {"service": "payment-service", "limit": 50}
        if tool_name in ("query_prometheus", "prometheus"):
            return {"query": 'rate(http_server_requests_seconds_count{status=~"5.."}[5m])'}
        if tool_name == "query_trace":
            return {"service": "payment-service", "limit": 10}
        return {}