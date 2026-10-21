"""诊断回调契约：状态/原因/候选/降级/token 必须随 payload 出网。

否则 CP 只能看到 rootCause，UNKNOWN/TIMEOUT 会被状态机当成 ROOT_CAUSE_FOUND，
前端也永远看不到降级原因。
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.consumer import submit_diagnosis
from app.main import _submit_diagnosis, _submit_verification
from app.models import DiagnosisResult, Evidence, VerificationResult


def _diagnosis() -> DiagnosisResult:
    return DiagnosisResult(
        root_cause="unknown",
        confidence=0.2,
        evidence=[Evidence(
            source="logs",
            key="redis",
            content="api_key=sk-1234567890 redis timeout",
        )],
        recommended_actions=[],
        status="UNKNOWN",
        fallback_used=True,
        heuristic_candidate="redis_connection_pool_exhausted",
        candidate_root_causes=["redis_connection_pool_exhausted"],
        llm_input_tokens=120,
        llm_output_tokens=30,
        reason_code="model_unknown",
    )


class DiagnosisPayloadContractTest(unittest.TestCase):
    def test_consumer_payload_carries_diagnosis_semantics(self):
        captured = {}

        def fake_request(method, url, payload=None, timeout=10, headers=None):
            captured.update(payload or {})
            return {}

        with patch("app.consumer._request_json", fake_request):
            submit_diagnosis("http://cp", 1, _diagnosis())

        self.assertEqual(captured["status"], "UNKNOWN")
        self.assertEqual(captured["reasonCode"], "model_unknown")
        self.assertEqual(captured["candidateRootCauses"], ["redis_connection_pool_exhausted"])
        self.assertTrue(captured["fallbackUsed"])
        self.assertEqual(captured["llmInputTokens"], 120)
        self.assertEqual(captured["llmOutputTokens"], 30)
        # 证据出网前必须脱敏（诊断路径已接线）
        self.assertIn("api_key=", captured["evidence"][0]["content"])
        self.assertNotIn("sk-1234567890", captured["evidence"][0]["content"])

    def test_sync_endpoint_payload_matches_consumer_contract(self):
        captured = {}

        class FakeResponse:
            status_code = 200

        def fake_post(url, json=None, timeout=10, headers=None):
            captured.update(json or {})
            return FakeResponse()

        with patch("app.main.httpx.post", fake_post):
            _submit_diagnosis(2, _diagnosis())

        self.assertEqual(captured["status"], "UNKNOWN")
        self.assertEqual(captured["reasonCode"], "model_unknown")
        self.assertEqual(captured["candidateRootCauses"], ["redis_connection_pool_exhausted"])
        self.assertTrue(captured["fallbackUsed"])
        self.assertEqual(captured["llmInputTokens"], 120)
        self.assertEqual(captured["llmOutputTokens"], 30)

    def test_verification_payload_is_masked_before_leaving_process(self):
        captured = {}

        def fake_post(url, json=None, timeout=10, headers=None):
            captured.update(json or {})
            return type("R", (), {"status_code": 200})()

        verification = VerificationResult(
            status="UNKNOWN",
            detail="api_key=sk-1234567890",
            evidence=[Evidence(source="prom", key="sli",
                               content="password=secret123 traceId=abc")],
        )
        with patch("app.main.httpx.post", fake_post):
            _submit_verification(4, verification)

        self.assertNotIn("sk-1234567890", captured["detail"])
        self.assertNotIn("secret123", captured["evidence"][0]["content"])
        self.assertIn("password=", captured["evidence"][0]["content"])


if __name__ == "__main__":
    unittest.main()
