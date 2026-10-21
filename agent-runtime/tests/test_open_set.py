"""开放诊断：prompt 不提供候选标签，模型可输出训练集外的 label 或 unknown。"""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.agent.diagnostic import RCA_CANDIDATE_LABELS, DiagnosticAgent
from app.llm.base import LLMProvider
from app.main import DiagnoseRequest, diagnose
from app.models import AgentState, DiagnosisResult, LLMResult
from app.tools.registry import ToolRegistry


class CapturingLLM(LLMProvider):
    def __init__(self, root_cause: str):
        self.root_cause = root_cause
        self.messages: list[list] = []

    def complete(self, messages, tools=None):
        self.messages.append(messages)
        return LLMResult(json.dumps({
            "rootCause": self.root_cause,
            "alternatives": [],
            "confidence": 0.8,
            "evidence": [],
            "recommendedActions": [],
        }), input_tokens=10, output_tokens=5)


def _agent(llm, open_set: bool) -> DiagnosticAgent:
    return DiagnosticAgent(llm, ToolRegistry(), open_set=open_set)


ALERT = {"service": "payment-service", "alertName": "HighLatency", "summary": "p99 elevated"}


class OpenSetDiagnosisTest(unittest.TestCase):
    def test_prompt_does_not_leak_candidate_labels(self):
        llm = CapturingLLM("network_policy_misconfiguration")
        result = _agent(llm, open_set=True).run(AgentState(incident_id=1, alert=ALERT))

        prompt = "\n".join(m.content for m in llm.messages[0])
        for label in RCA_CANDIDATE_LABELS:
            self.assertNotIn(label, prompt, f"open-set prompt leaked label {label}")
        self.assertEqual(result.root_cause, "network_policy_misconfiguration")
        self.assertEqual(result.status, "ROOT_CAUSE_FOUND")

    def test_open_set_accepts_label_outside_closed_set(self):
        llm = CapturingLLM("Network-Policy Misconfiguration")
        result = _agent(llm, open_set=True).run(AgentState(incident_id=2, alert=ALERT))

        self.assertEqual(result.root_cause, "Network-Policy Misconfiguration")
        self.assertEqual(result.candidate_root_causes[0], "network_policy_misconfiguration")

    def test_closed_set_still_rejects_outside_label(self):
        llm = CapturingLLM("network_policy_misconfiguration")
        result = _agent(llm, open_set=False).run(AgentState(incident_id=3, alert=ALERT))

        self.assertEqual(result.root_cause, "unknown")
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.reason_code, "invalid_label")

    def test_open_set_unknown_abstains(self):
        llm = CapturingLLM("unknown")
        result = _agent(llm, open_set=True).run(AgentState(incident_id=4, alert=ALERT))

        self.assertEqual(result.root_cause, "unknown")
        self.assertEqual(result.status, "UNKNOWN")
        self.assertTrue(result.fallback_used)


class EvaluationNoWritebackTest(unittest.TestCase):
    def _runner(self):
        diagnosis = DiagnosisResult(
            root_cause="network_policy_misconfiguration", confidence=0.8)

        class Runner:
            def run_diagnosis(self, incident_id, alert, run_key=None):
                return SimpleNamespace(
                    diagnosis=diagnosis,
                    state=AgentState(incident_id=incident_id, alert=alert),
                    duration_ms=0,
                    resumed=False,
                )

        return Runner()

    def test_submit_result_false_does_not_spawn_callback(self):
        request = DiagnoseRequest(incident_id=1, alert=ALERT, open_set=True,
                                  submit_result=False)
        with patch("app.main._build_runner", return_value=self._runner()), \
                patch("app.main.threading.Thread") as thread:
            diagnose(request)
        thread.assert_not_called()

    def test_submit_result_true_spawns_callback(self):
        request = DiagnoseRequest(incident_id=1, alert=ALERT, open_set=True)
        with patch("app.main._build_runner", return_value=self._runner()), \
                patch("app.main.threading.Thread") as thread:
            diagnose(request)
        thread.assert_called_once()
        thread.return_value.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
