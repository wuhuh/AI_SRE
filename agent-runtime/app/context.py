"""Context management: keep recent steps, evidence summaries and budget."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import AgentState, Evidence, ToolCall

MAX_RECENT_STEPS = 8
MAX_CONTEXT_CHARS = 12_000


@dataclass
class ContextBundle:
    summary: str
    recent_steps: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    tool_results: list[str] = field(default_factory=list)
    token_estimate: int = 0

    def to_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "You are a precise SRE diagnostic agent."},
            {"role": "user", "content": self.summary},
        ]


def build_context(state: AgentState, alert: dict[str, Any]) -> ContextBundle:
    summary_parts = [
        f"Incident #{state.incident_id}",
        f"service={alert.get('service')}",
        f"alert={alert.get('alertName')}",
        f"severity={alert.get('severity')}",
        f"summary={alert.get('summary')}",
    ]
    recent = [
        f"{t.name}({t.status}) -> {t.result_summary or t.error}"
        for t in state.tool_calls[-MAX_RECENT_STEPS:]
    ]
    evidence_summaries = [f"{e.source}:{e.key} = {e.content}" for e in state.evidence[-5:]]
    tool_summaries = [f"{name}: {result[:200]}" for name, result in state.tool_results.items()]
    summary = "\n".join(summary_parts + ["Recent tool calls:"] + recent + ["Evidence:"] + evidence_summaries + ["Tool results:"] + tool_summaries)
    if len(summary) > MAX_CONTEXT_CHARS:
        summary = summary[:MAX_CONTEXT_CHARS] + "...[truncated]"
    return ContextBundle(summary=summary, recent_steps=recent, evidence=state.evidence, tool_results=tool_summaries)