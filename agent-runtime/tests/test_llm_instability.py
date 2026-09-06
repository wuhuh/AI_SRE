import json
import unittest

from app.agent.diagnostic import DiagnosticAgent
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models import AgentState, LLMResult
from app.tools.registry import ToolRegistry
from test_core import EchoTool


class InfiniteLoopLLM(LLMProvider):
    def complete(self, messages, tools=None):
        return LLMResult(json.dumps({"nextTool": "echo"}), input_tokens=1, output_tokens=1)


class LLMInstabilityTest(unittest.TestCase):
    def test_invalid_json_returns_graceful_result(self):
        # P0-01: LLM 失效时规则兜底必须降级（unknown + 低置信 + fallbackUsed），
        # 不再用关键词映射冒充根因（旧行为曾被此测试断言为 bug 修复）。
        registry = ToolRegistry()
        registry.register(EchoTool())
        agent = DiagnosticAgent(llm=MockLLMProvider(mode="invalid_json"), registry=registry)
        state = AgentState(incident_id=1, alert={"summary": "redis"})
        result = agent.run(state)
        self.assertEqual(result.root_cause, "unknown")
        self.assertLessEqual(result.confidence, 0.3)
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.heuristic_candidate, "redis_connection_pool_exhausted")

    def test_unknown_tool_as_plan_does_not_break(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        agent = DiagnosticAgent(llm=MockLLMProvider(), registry=registry)
        state = AgentState(incident_id=1, alert={"summary": "redis"})
        state.plan = ["not_exist"]
        result = agent.run(state)
        # Unknown tool names are filtered out before execution, so no invalid ToolCall is created.
        self.assertEqual(result.tool_calls, [])

    def test_infinite_loop_is_bounded_by_max_steps(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        agent = DiagnosticAgent(llm=InfiniteLoopLLM(), registry=registry, max_steps=3)
        state = AgentState(incident_id=1, alert={"summary": "redis"})
        result = agent.run(state)
        self.assertLessEqual(state.step, 3)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
