"""文档 8.6/8.5：闭集根因代码级校验 + UNKNOWN reason_code。

模型编出的非法标签不能因为「不是 unknown 字符串」就被视为已找到根因，
必须走与 unknown 相同的降级路径并清理动作建议。
"""
from __future__ import annotations

import unittest

from app.agent.diagnostic import RCA_CANDIDATE_LABELS, DiagnosticAgent
from app.llm.base import LLMProvider, LLMResult
from app.llm.mock import MockLLMProvider
from app.models import AgentState
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry


class OkTool(Tool):
    spec = ToolSpec(
        name="query_prometheus",
        description="ok",
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level="READ_ONLY",
    )

    def execute(self, arguments, principal="agent"):
        return "{}"


def _llm(content: str) -> LLMProvider:
    class Fixed(LLMProvider):
        def complete(self, messages, tools=None):
            return LLMResult(content, input_tokens=10, output_tokens=5)
    return Fixed()


def _agent(llm: LLMProvider) -> DiagnosticAgent:
    registry = ToolRegistry()
    registry.register(OkTool())
    return DiagnosticAgent(llm, registry, retriever=None)


def _state() -> AgentState:
    state = AgentState(incident_id=1, alert={"service": "payment"})
    state.plan = ["query_prometheus"]
    return state


class InvalidRootLabelTest(unittest.TestCase):
    def test_hallucinated_label_becomes_unknown_with_reason_code(self):
        agent = _agent(_llm(
            '{"rootCause": "banana_peel", "confidence": 0.9, '
            '"evidence": [], "recommendedActions": ["restart_pod"]}'))
        state = _state()
        state.pending = ["query_prometheus"]
        result = agent.run(state)

        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.root_cause, "unknown")
        self.assertEqual(result.reason_code, "invalid_label")
        # 文档 8.5：非法标签上的动作建议必须被清理
        self.assertEqual(result.recommended_actions, [])
        self.assertLessEqual(result.confidence, 0.3)

    def test_valid_label_is_adopted_with_reason_code_empty(self):
        valid = RCA_CANDIDATE_LABELS[0]
        agent = _agent(_llm(
            '{"rootCause": "%s", "confidence": 0.8, "evidence": [], '
            '"recommendedActions": []}' % valid))
        state = _state()
        state.pending = ["query_prometheus"]
        result = agent.run(state)

        self.assertEqual(result.status, "ROOT_CAUSE_FOUND")
        self.assertEqual(result.root_cause, valid)
        self.assertEqual(result.reason_code, "")

    def test_model_unknown_has_reason_code(self):
        agent = _agent(_llm(
            '{"rootCause": "unknown", "confidence": 0.0, "evidence": [], '
            '"recommendedActions": []}'))
        state = _state()
        state.pending = ["query_prometheus"]
        result = agent.run(state)

        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.reason_code, "model_unknown")


if __name__ == "__main__":
    unittest.main()
