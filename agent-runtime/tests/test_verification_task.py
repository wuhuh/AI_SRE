"""Verification 持久任务：消费者按 task.type 分支，领取后执行验证并回调。

回归背景：验证原先由 CP 同步 HTTP 调用 Agent /verify，默认观察窗 60s
而 CP 超时只有 30s——CP 必然超时，且长 HTTP 调用被包在事务里。
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.consumer import consume_once
from app.models import Evidence, VerificationResult


class StubRunner:
    def __init__(self, submit_should_fail: bool = False):
        self.run_keys: list[str | None] = []
        self.diagnosis_called = False
        self.submit_should_fail = submit_should_fail

    def run_verification(self, state, run_key=None):
        self.run_keys.append(run_key)
        return SimpleNamespace(verification=VerificationResult(
            status="RECOVERED",
            detail="error rate back to baseline",
            evidence=[Evidence(source="prometheus", key="sli", content="error_rate=0.001")],
        ))

    def run_diagnosis(self, incident_id, alert, run_key=None):
        self.diagnosis_called = True
        raise AssertionError("verification task must not run diagnosis")


def _fake_cp(calls: list[tuple[str, str, dict | None]], submit_should_fail: bool):
    def fake_request(method, url, payload=None, timeout=10, headers=None):
        calls.append((method, url, payload))
        if "/tasks/pending" in url and method == "GET":
            return [{"id": 9, "incidentId": 3, "type": "VERIFICATION"}]
        if "/claim" in url:
            return {"claimed": True, "task": {"claimEpoch": 1}}
        if "/incidents/3" in url and method == "GET":
            return {"id": 3, "service": "payment-service", "severity": "P1", "summary": "recovered?"}
        if "/verification" in url:
            if submit_should_fail:
                raise RuntimeError("control-plane down")
            return {}
        if "/complete" in url:
            return {}
        if "/fail" in url:
            return {}
        return {}
    return fake_request


class VerificationTaskTest(unittest.TestCase):
    def test_verification_task_runs_verification_and_completes(self):
        calls: list[tuple[str, str, dict | None]] = []
        runner = StubRunner()

        with patch("app.consumer._request_json", _fake_cp(calls, False)):
            processed = consume_once(runner, "http://cp")

        self.assertEqual(processed, 1)
        self.assertEqual(runner.run_keys, ["verify-9"])
        self.assertFalse(runner.diagnosis_called)
        verification_calls = [c for c in calls if "/verification" in c[1]]
        self.assertEqual(len(verification_calls), 1)
        payload = verification_calls[0][2]
        self.assertEqual(payload["status"], "RECOVERED")
        self.assertEqual(payload["taskId"], 9)
        self.assertTrue(any("/complete" in c[1] for c in calls))
        self.assertFalse(any("/fail" in c[1] for c in calls))

    def test_verification_submit_failure_fails_task_and_skips_complete(self):
        calls: list[tuple[str, str, dict | None]] = []
        runner = StubRunner()
        env = {"SUBMIT_RETRY_DELAY_SECONDS": "0.01", "SUBMIT_MAX_RETRIES": "0"}

        with patch("app.consumer._request_json", _fake_cp(calls, True)), \
                patch.dict("os.environ", env):
            processed = consume_once(runner, "http://cp")

        self.assertEqual(processed, 0)
        self.assertTrue(any("/fail" in c[1] for c in calls))
        self.assertFalse(any("/complete" in c[1] for c in calls))


if __name__ == "__main__":
    unittest.main()
