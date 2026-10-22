"""P0-01: 规则兜底必须降级（unknown + 低置信 + fallbackUsed），不得冒充结论或伪造证据。"""
from __future__ import annotations

import json
import unittest

from app.agent.diagnostic import RETRYABLE_REASON_CODES, DiagnosticAgent
from app.llm.mock import MockLLMProvider
from app.models import AgentState, LLMResult
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry

ALERT = {"service": "payment-service", "alertName": "latency", "summary": "payment p99 high"}


class OkTool(Tool):
    spec = ToolSpec(
        name="query_prometheus",
        description="ok",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": []},
        risk_level="READ_ONLY",
    )

    def execute(self, arguments, principal="agent"):
        return '{"status":"success"}'


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(OkTool())
    return registry


class FallbackDegradationTest(unittest.TestCase):
    def test_invalid_json_degrades_to_unknown_low_confidence(self):
        agent = DiagnosticAgent(MockLLMProvider(mode="invalid_json"), _registry())
        result = agent.run(AgentState(incident_id=1, alert=ALERT))
        self.assertEqual(result.root_cause, "unknown")
        self.assertLessEqual(result.confidence, 0.3)
        self.assertTrue(result.fallback_used)
        self.assertIsNotNone(result.heuristic_candidate)
        self.assertEqual(result.recommended_actions, [])
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.reason_code, "invalid_json")

    def test_no_rule_evidence_fabricated(self):
        agent = DiagnosticAgent(MockLLMProvider(mode="invalid_json"), _registry())
        result = agent.run(AgentState(incident_id=1, alert=ALERT))
        self.assertFalse(any(e.source == "rule" for e in result.evidence))

    def test_timeout_gets_distinct_timeout_semantics(self):
        # P2-AR-09: 超时是独立语义（TIMEOUT），不再伪装成 UNKNOWN/降级；
        # 不伪造根因的守卫不变：root 仍 unknown、不给修复建议
        agent = DiagnosticAgent(MockLLMProvider(), _registry(), max_duration_seconds=-1.0)
        state = AgentState(incident_id=2, alert=ALERT)
        result = agent.run(state)
        self.assertEqual(result.root_cause, "unknown")
        self.assertEqual(result.status, "TIMEOUT")
        self.assertFalse(result.fallback_used)
        self.assertEqual(result.recommended_actions, [])
        self.assertEqual(result.reason_code, "timeout")
        self.assertEqual(state.error, "diagnosis_timeout")

    def test_normal_llm_result_is_kept_as_is(self):
        agent = DiagnosticAgent(MockLLMProvider(), _registry())
        result = agent.run(AgentState(incident_id=3, alert=ALERT))
        self.assertEqual(result.root_cause, "redis_connection_pool_exhausted")
        self.assertAlmostEqual(result.confidence, 0.91)
        self.assertFalse(result.fallback_used)
        self.assertIsNone(result.heuristic_candidate)
        self.assertEqual(result.status, "ROOT_CAUSE_FOUND")
        self.assertEqual(result.reason_code, "")

    def test_llm_transport_error_gets_llm_error_reason(self):
        class RaisingLLM:
            def complete(self, messages, tools=None):
                raise ConnectionResetError("connection reset by peer")

        agent = DiagnosticAgent(RaisingLLM(), _registry())
        result = agent.run(AgentState(incident_id=4, alert=ALERT))

        self.assertEqual(result.root_cause, "unknown")
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.reason_code, "llm_error")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.llm_input_tokens, 0)

    def test_model_explicit_unknown_is_not_retryable(self):
        class UnknownLLM:
            def complete(self, messages, tools=None):
                return LLMResult(json.dumps({
                    "rootCause": "unknown",
                    "confidence": 0.0,
                    "evidence": [],
                    "recommendedActions": [],
                }), input_tokens=10, output_tokens=5)

        agent = DiagnosticAgent(UnknownLLM(), _registry())
        result = agent.run(AgentState(incident_id=5, alert=ALERT))

        self.assertEqual(result.reason_code, "model_unknown")
        self.assertEqual(result.status, "UNKNOWN")

    def test_retryable_reason_codes_stay_narrow(self):
        # 只允许环境/解析抖动重试；模型拒答、非法标签、超时都不是重试理由
        self.assertEqual(RETRYABLE_REASON_CODES, {"llm_error", "invalid_json"})
        for code in ("model_unknown", "invalid_label", "timeout"):
            self.assertNotIn(code, RETRYABLE_REASON_CODES)


if __name__ == "__main__":
    unittest.main()
