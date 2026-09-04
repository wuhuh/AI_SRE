"""Baseline comparison: Alert+LLM vs Alert+RAG+LLM vs Full Agent Tool Calling.

This script is runnable without Docker. It uses the actual Agent Runtime core with
a controlled evidence-aware LLM so the comparison is reproducible.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent-runtime"))

from app.agent.diagnostic import DiagnosticAgent
from app.llm.base import LLMProvider, Message
from app.models import AgentState, LLMResult
from app.rag.retriever import Document, HybridRetriever
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry

DOCS = [
    Document(id="redis-pool", title="Redis connection pool exhausted", content="redis maxclients reached pool exhausted", tags=["redis"]),
    Document(id="slow-sql", title="Slow SQL", content="slow query database latency", tags=["slow sql"]),
    Document(id="cpu-sat", title="CPU saturation", content="cpu usage 100 percent saturation", tags=["cpu"]),
]

CASES = [
    {"id": "redis_001", "summary": "payment latency high", "expected": "redis_connection_pool_exhausted", "tool": "redis maxclients reached"},
    {"id": "slow_sql_001", "summary": "order creation slow", "expected": "slow_sql", "tool": "slow query log detected"},
    {"id": "cpu_001", "summary": "inventory high load", "expected": "cpu_saturation", "tool": "cpu usage 100 percent"},
]


class EvidenceAwareLLM(LLMProvider):
    def complete(self, messages: list[Message], tools=None) -> LLMResult:
        content = "\n".join(m.content for m in messages if m.role == "user")
        lowered = content.lower()
        # Prefer direct tool evidence when present.
        tool_evidence = None
        rag_evidence = None
        for line in lowered.splitlines():
            if line.startswith("evidence_tool:"):
                tool_evidence = line.split(":", 1)[1]
            if line.startswith("retrieve_runbook:"):
                rag_evidence = line.split(":", 1)[1]
        evidence = tool_evidence or rag_evidence or content
        if "slow query" in evidence or "slow sql" in evidence or "slow_sql" in evidence:
            root = "slow_sql"
        elif "redis" in evidence or "maxclients" in evidence:
            root = "redis_connection_pool_exhausted"
        elif "cpu" in evidence or "saturation" in evidence or "100 percent" in evidence:
            root = "cpu_saturation"
        else:
            root = "unknown"
        return LLMResult(json.dumps({
            "rootCause": root,
            "confidence": 0.9,
            "evidence": [],
            "recommendedActions": [],
        }), input_tokens=100, output_tokens=50)


class EvidenceTool(Tool):
    spec = ToolSpec(
        name="evidence_tool",
        description="return evidence",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        risk_level="READ_ONLY",
    )

    def execute(self, arguments, principal="agent"):
        return arguments.get("query", "")


def evaluate(registry, retriever, use_rag: bool, use_tools: bool) -> dict:
    llm = EvidenceAwareLLM()
    agent = DiagnosticAgent(llm=llm, registry=registry, retriever=retriever)
    correct = 0
    results = []
    for case in CASES:
        state = AgentState(incident_id=0, alert={"service": "demo", "summary": case["summary"]})
        state.plan = []
        if use_rag:
            state.plan.append("retrieve_runbook")
        if use_tools:
            state.plan.append("evidence_tool")
            state.alert["tool_hint"] = case["tool"]
        # DiagnosticAgent._tool_arguments does not know evidence_tool; adapt by patching arguments.
        original = agent._tool_arguments
        def args_for(state, name, _orig=original, hint=case["tool"]):
            if name == "evidence_tool":
                return {"query": hint}
            return _orig(state, name)
        agent._tool_arguments = args_for
        result = agent.run(state)
        agent._tool_arguments = original
        ok = result.root_cause == case["expected"]
        correct += 1 if ok else 0
        results.append({"case": case["id"], "expected": case["expected"], "actual": result.root_cause, "ok": ok})
    return {"accuracy": correct / len(CASES), "results": results}


def main() -> None:
    retriever = HybridRetriever(DOCS, top_k=2)
    empty_registry = ToolRegistry()
    tool_registry = ToolRegistry()
    tool_registry.register(EvidenceTool())

    baseline_a = evaluate(empty_registry, None, use_rag=False, use_tools=False)
    baseline_b = evaluate(empty_registry, retriever, use_rag=True, use_tools=False)
    final = evaluate(tool_registry, retriever, use_rag=True, use_tools=True)

    report = {
        "baseline_a_alert_llm": baseline_a["accuracy"],
        "baseline_b_alert_rag_llm": baseline_b["accuracy"],
        "final_alert_tools_rag_llm": final["accuracy"],
        "details": {
            "baseline_a": baseline_a["results"],
            "baseline_b": baseline_b["results"],
            "final": final["results"],
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()