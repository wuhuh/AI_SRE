"""P0-03: 约束化标签输出 + alternatives 候选列表 + token 计量。"""
from __future__ import annotations

import unittest

from app.agent.diagnostic import DiagnosticAgent, RCA_CANDIDATE_LABELS, normalize_label
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


class AlternativesLLM(LLMProvider):
    def complete(self, messages, tools=None):
        return LLMResult(
            '{"rootCause": "Slow SQL", "alternatives": ["Database-Connection-Pool-Exhausted", '
            '"unknown", "Slow SQL"], "confidence": 0.7, "evidence": [], "recommendedActions": []}',
            input_tokens=120,
            output_tokens=30,
        )


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(OkTool())
    return registry


ALERT = {"service": "payment-service", "summary": "p99 latency elevated"}


class CandidateRootCausesTest(unittest.TestCase):
    def test_alternatives_normalized_deduped_capped(self):
        agent = DiagnosticAgent(AlternativesLLM(), _registry())
        result = agent.run(AgentState(incident_id=1, alert=ALERT))
        self.assertEqual(
            result.candidate_root_causes,
            ["slow_sql", "database_connection_pool_exhausted"],
        )
        self.assertEqual(result.root_cause, "Slow SQL")

    def test_fallback_candidates_only_heuristic(self):
        agent = DiagnosticAgent(MockLLMProvider(mode="invalid_json"), _registry())
        result = agent.run(AgentState(incident_id=2, alert=ALERT))
        self.assertEqual(result.candidate_root_causes, [result.heuristic_candidate])
        self.assertEqual(len(result.candidate_root_causes), 1)

    def test_mock_normal_keeps_single_candidate(self):
        agent = DiagnosticAgent(MockLLMProvider(), _registry())
        result = agent.run(AgentState(incident_id=3, alert=ALERT))
        self.assertEqual(result.candidate_root_causes, ["redis_connection_pool_exhausted"])

    def test_token_metering_accumulates(self):
        agent = DiagnosticAgent(AlternativesLLM(), _registry())
        result = agent.run(AgentState(incident_id=4, alert=ALERT))
        self.assertEqual(result.llm_input_tokens, 120)
        self.assertEqual(result.llm_output_tokens, 30)

    def test_label_set_covers_ten_faults(self):
        self.assertEqual(len(RCA_CANDIDATE_LABELS), 10)
        for label in RCA_CANDIDATE_LABELS:
            self.assertEqual(normalize_label(label), label)


if __name__ == "__main__":
    unittest.main()
