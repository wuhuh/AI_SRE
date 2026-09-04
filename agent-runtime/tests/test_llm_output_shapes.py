"""P0-03: 真实 LLM 输出形状多变 —— _finalize 必须宽容解析而不是 500。"""
from __future__ import annotations

import json
import unittest

from app.agent.diagnostic import DiagnosticAgent
from app.llm.base import LLMProvider, LLMResult
from app.models import AgentState
from app.tools.registry import ToolRegistry


class MessyLLM(LLMProvider):
    """模拟真实 LLM 的形状漂移：evidence 为字符串列表 + confidence 为字符串。"""

    def complete(self, messages, tools=None):
        return LLMResult(json.dumps({
            "rootCause": "slow_sql",
            "alternatives": "database_connection_pool_exhausted",
            "confidence": "0.7",
            "evidence": ["queries take 3s at p99", {"source": "prometheus", "key": "lat", "content": "p95 high"}],
            "recommendedActions": "add index on orders(user_id)",
        }), input_tokens=10, output_tokens=5)


class JunkConfidenceLLM(LLMProvider):
    def complete(self, messages, tools=None):
        return LLMResult(json.dumps({"rootCause": "slow_sql", "confidence": "high"}),
                         input_tokens=1, output_tokens=1)


def _agent(llm) -> DiagnosticAgent:
    return DiagnosticAgent(llm, ToolRegistry())


class MessyOutputTest(unittest.TestCase):
    def test_string_evidence_and_scalar_actions_survive(self):
        result = _agent(MessyLLM()).run(AgentState(incident_id=1, alert={"summary": "latency"}))
        self.assertEqual(result.root_cause, "slow_sql")
        self.assertAlmostEqual(result.confidence, 0.7)
        self.assertEqual(result.recommended_actions, ["add index on orders(user_id)"])
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(result.candidate_root_causes, ["slow_sql", "database_connection_pool_exhausted"])

    def test_non_numeric_confidence_defaults_to_zero(self):
        result = _agent(JunkConfidenceLLM()).run(AgentState(incident_id=2, alert={"summary": "latency"}))
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.root_cause, "slow_sql")


if __name__ == "__main__":
    unittest.main()
