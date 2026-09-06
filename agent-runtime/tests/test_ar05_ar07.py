"""P1-AR-05 / P1-AR-07 语义单测。"""
import os
import time
import unittest
from unittest.mock import patch

from app.consumer import consume_once
from app.models import DiagnosisResult
from app.tools.base import Tool, ToolSpec


class _StubRunner:
    def __init__(self, diagnosis):
        self.diagnosis = diagnosis

    def run_diagnosis(self, incident_id, alert):
        return type("R", (), {"diagnosis": self.diagnosis})()


def _diagnosis():
    return DiagnosisResult(
        root_cause="x",
        confidence=0.9,
        evidence=[],
        recommended_actions=["restart_pod"],
        tool_calls=[],
    )


class AR05ConsumerSubmitTest(unittest.TestCase):
    def test_submit_failure_marks_task_failed_and_never_completes(self):
        calls = []

        def fake_request(method, url, payload=None, timeout=10, headers=None):
            calls.append((method, url))
            if "/tasks/pending" in url and method == "GET":
                return [{"id": 7, "incidentId": 3, "type": "DIAGNOSIS"}]
            if "/claim" in url:
                return {"claimed": True}
            if "/incidents/3" in url and method == "GET":
                return {"id": 3, "service": "s", "severity": "P1", "summary": "x"}
            if "/diagnosis" in url:
                raise RuntimeError("control-plane down")
            if "/complete" in url:
                return {}
            if "/fail" in url:
                return {}
            return {}

        env = {"SUBMIT_RETRY_DELAY_SECONDS": "0.01"}
        with patch("app.consumer._request_json", fake_request), patch.dict(os.environ, env):
            processed = consume_once(_StubRunner(_diagnosis()), "http://cp", idempotency_store=None)
        self.assertEqual(processed, 0)
        self.assertTrue(any("/fail" in u for _, u in calls), "task must be failed on submit error")
        self.assertFalse(any("/complete" in u for _, u in calls),
                         "complete must NOT be called when submit fails")

    def test_submit_succeeds_then_completes_and_marks_processed(self):
        calls = []

        def fake_request(method, url, payload=None, timeout=10, headers=None):
            calls.append((method, url))
            if "/tasks/pending" in url:
                return [{"id": 7, "incidentId": 3, "type": "DIAGNOSIS"}]
            if "/claim" in url:
                return {"claimed": True}
            if "/incidents/3" in url:
                return {"id": 3, "service": "s", "severity": "P1", "summary": "x"}
            return {}

        marked = []
        store = type("S", (), {"is_processed": lambda self, k: False,
                               "mark_processed": lambda self, k: marked.append(k)})()
        with patch("app.consumer._request_json", fake_request):
            consume_once(_StubRunner(_diagnosis()), "http://cp", idempotency_store=store)
        self.assertTrue(any("/complete" in u for _, u in calls), "task should complete on success")
        self.assertEqual(marked, ["7:DIAGNOSIS"], "mark_processed must run after complete")


class AR07ToolTimeoutTest(unittest.TestCase):
    def test_slow_tool_is_enforced_to_timeout(self):
        class SlowTool(Tool):
            spec = ToolSpec(name="slow", description="d", timeout_seconds=0.2)

            def execute(self, arguments, principal="agent"):
                time.sleep(2)
                return "late"

        result = SlowTool().call({}, principal="agent")
        self.assertEqual(result.status, "TIMEOUT")
        self.assertLess(result.duration_ms, 1500, "timeout must cut the wait near the spec budget")

    def test_fast_tool_still_succeeds(self):
        class FastTool(Tool):
            spec = ToolSpec(name="fast", description="d", timeout_seconds=5)

            def execute(self, arguments, principal="agent"):
                return "ok"

        result = FastTool().call({}, principal="agent")
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.result_summary, "ok")


if __name__ == "__main__":
    unittest.main()
