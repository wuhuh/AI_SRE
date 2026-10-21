"""Native function calling：工具 schema 下发、tool_calls 解析、参数由模型提供。

保留旧 nextTool 协议的同时，验证新路径：
- LLM 收到 tools schema（含 retrieve_runbook 合成工具）；
- tool_calls 的 arguments 原样执行，不再走告警驱动的硬编码参数；
- assistant/tool 消息按 tool_call_id 回灌，形成可续跑的多轮对话；
- 非法参数不会炸穿诊断循环，结构化 ERROR 后模型可继续收敛。
"""
from __future__ import annotations

import json
import unittest

from app.agent.diagnostic import DiagnosticAgent
from app.llm.base import LLMProvider
from app.models import AgentState, LLMResult
from app.rag.retriever import Document
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry


class RecordingTool(Tool):
    def __init__(self, name: str, parameters: dict):
        self.spec = ToolSpec(
            name=name,
            description="recording tool",
            parameters=parameters,
            risk_level="READ_ONLY",
        )
        self.seen: list[dict] = []

    def execute(self, arguments, principal="agent"):
        self.seen.append(arguments)
        return '{"status":"success"}'


class RecordingRetriever:
    def __init__(self):
        self.queries: list[str] = []

    def retrieve(self, query: str):
        self.queries.append(query)
        return [Document(id="redis-pool", title="Redis pool", content="maxclients reached")]


class ScriptedLLM(LLMProvider):
    def __init__(self, responses: list[LLMResult]):
        self.responses = list(responses)
        self.calls = 0
        self.seen_tools: list[list[dict] | None] = []

    def complete(self, messages, tools=None):
        self.calls += 1
        self.seen_tools.append(tools)
        return self.responses.pop(0)


def _tool_call(name: str, arguments, call_id: str = "call_1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
        },
    }


def _final(root: str = "slow_sql") -> LLMResult:
    return LLMResult(
        json.dumps({
            "rootCause": root,
            "confidence": 0.8,
            "evidence": [],
            "recommendedActions": [],
        }),
        input_tokens=20,
        output_tokens=10,
    )


def _registry_with(recorder: RecordingTool) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(recorder)
    return registry


ALERT = {"service": "payment-service", "alertName": "HighLatency", "summary": "p99 high"}


class NativeToolCallingTest(unittest.TestCase):
    def test_llm_arguments_are_used_and_tool_schema_is_sent(self):
        recorder = RecordingTool(
            "query_prometheus",
            {"type": "object", "properties": {"query": {"type": "string"}},
             "required": ["query"]},
        )
        llm = ScriptedLLM([
            LLMResult("", tool_calls=[_tool_call(
                "query_prometheus", {"query": "custom_metric_query"})],
                input_tokens=10, output_tokens=5),
            _final(),
        ])
        state = AgentState(incident_id=1, alert=ALERT)
        state.plan = []  # 跳过固定计划，直接走 LLM 决策

        result = DiagnosticAgent(llm, _registry_with(recorder)).run(state)

        self.assertEqual(recorder.seen, [{"query": "custom_metric_query"}])
        self.assertEqual(result.root_cause, "slow_sql")
        self.assertEqual(result.tool_calls[0].arguments, {"query": "custom_metric_query"})
        self.assertEqual(llm.calls, 2)

        names = {s["function"]["name"] for s in llm.seen_tools[0]}
        self.assertIn("query_prometheus", names)
        self.assertIn("retrieve_runbook", names)

        roles = [m["role"] for m in state.llm_messages]
        self.assertEqual(roles[:2], ["system", "user"])
        self.assertIn("assistant", roles)
        self.assertIn("tool", roles)
        tool_message = next(m for m in state.llm_messages if m["role"] == "tool")
        self.assertEqual(tool_message["tool_call_id"], "call_1")

    def test_invalid_tool_arguments_become_structured_error(self):
        recorder = RecordingTool(
            "query_prometheus",
            {"type": "object", "properties": {"query": {"type": "string"}},
             "required": ["query"]},
        )
        llm = ScriptedLLM([
            LLMResult("", tool_calls=[_tool_call("query_prometheus", "{not-json")],
                      input_tokens=1, output_tokens=1),
            _final(),
        ])
        state = AgentState(incident_id=2, alert=ALERT)
        state.plan = []

        result = DiagnosticAgent(llm, _registry_with(recorder)).run(state)

        self.assertEqual(recorder.seen, [])
        self.assertEqual(result.tool_calls[0].status, "ERROR")
        self.assertIn("Missing required", result.tool_calls[0].error)
        self.assertEqual(result.root_cause, "slow_sql")

    def test_native_retrieve_runbook_uses_model_query(self):
        retriever = RecordingRetriever()
        llm = ScriptedLLM([
            LLMResult("", tool_calls=[_tool_call("retrieve_runbook", {"query": "redis pool"})],
                      input_tokens=1, output_tokens=1),
            _final("redis_connection_pool_exhausted"),
        ])
        state = AgentState(incident_id=3, alert=ALERT)
        state.plan = []

        result = DiagnosticAgent(llm, ToolRegistry(), retriever=retriever).run(state)

        self.assertEqual(retriever.queries, ["redis pool"])
        self.assertEqual(result.tool_calls[0].name, "retrieve_runbook")
        self.assertEqual(result.tool_calls[0].arguments, {"query": "redis pool"})
        rag = next(e for e in result.evidence if e.source == "rag")
        self.assertEqual(rag.query, "redis pool")

    def test_tool_calls_at_step_limit_still_get_tool_responses(self):
        # OpenAI 协议要求每个 tool_call 都有 tool 响应；max_steps 截断时
        # 未执行的调用也必须回一条 SKIPPED，否则下一次请求会 400。
        recorder = RecordingTool(
            "query_prometheus",
            {"type": "object", "properties": {"query": {"type": "string"}},
             "required": ["query"]},
        )
        llm = ScriptedLLM([
            LLMResult("", tool_calls=[
                _tool_call("query_prometheus", {"query": "q1"}, "call_1"),
                _tool_call("query_prometheus", {"query": "q2"}, "call_2"),
            ], input_tokens=1, output_tokens=1),
            _final(),
        ])
        state = AgentState(incident_id=5, alert=ALERT)
        state.plan = []

        result = DiagnosticAgent(
            llm, _registry_with(recorder), max_steps=1).run(state)

        tool_messages = [m for m in state.llm_messages if m["role"] == "tool"]
        by_id = {m["tool_call_id"]: m["content"] for m in tool_messages}
        self.assertIn("call_1", by_id)
        self.assertIn("call_2", by_id)
        self.assertIn("SKIPPED", by_id["call_2"])
        self.assertEqual(recorder.seen, [{"query": "q1"}])
        self.assertEqual(result.root_cause, "slow_sql")

    def test_unknown_native_tool_is_reported_then_loop_continues(self):
        llm = ScriptedLLM([
            LLMResult("", tool_calls=[_tool_call("hack_tool", {})],
                      input_tokens=1, output_tokens=1),
            _final(),
        ])
        state = AgentState(incident_id=4, alert=ALERT)
        state.plan = []

        result = DiagnosticAgent(llm, ToolRegistry()).run(state)

        self.assertEqual(result.tool_calls, [])
        self.assertEqual(result.root_cause, "slow_sql")
        tool_message = next(m for m in state.llm_messages if m["role"] == "tool")
        self.assertIn("unknown tool", tool_message["content"])
        self.assertEqual(llm.calls, 2)


if __name__ == "__main__":
    unittest.main()
