from __future__ import annotations

import json

from app.llm.base import LLMProvider, Message
from app.models import AgentState

DEFAULT_PLAN = [
    "query_prometheus",
    "query_logs",
    "query_trace",
    "retrieve_runbook",
]


class Planner:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def plan(self, state: AgentState) -> list[str]:
        prompt = (
            "You are an SRE planner. Analyze the alert and output JSON {\"plan\": [tool names]}.\n"
            f"Alert: {state.alert}"
        )
        try:
            result = self.llm.complete([Message(role="user", content=prompt)])
            data = json.loads(result.content)
            plan = data.get("plan", [])
            return plan if isinstance(plan, list) and plan else DEFAULT_PLAN
        except Exception:
            return DEFAULT_PLAN