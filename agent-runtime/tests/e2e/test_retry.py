"""E2E 重试策略单测（不依赖 Docker / 网络）。"""
from __future__ import annotations

import os
import unittest
import urllib.error
from unittest.mock import patch

from tests.e2e.retry import (
    TransientE2EError,
    is_retryable_exception,
    is_transient_diagnosis,
    retry_transient,
)


class Dummy:
    def __init__(self):
        self.calls = 0
        self.resets = 0

    def _reset_faults(self):
        self.resets += 1


class DiagnosisClassificationTest(unittest.TestCase):
    def test_zero_token_is_transient(self):
        self.assertTrue(is_transient_diagnosis(
            {"diagnosis": {"llm_input_tokens": 0, "status": "UNKNOWN"}}))

    def test_agent_timeout_is_transient(self):
        self.assertTrue(is_transient_diagnosis(
            {"diagnosis": {"llm_input_tokens": 10, "status": "TIMEOUT"}}))

    def test_invalid_json_is_transient(self):
        self.assertTrue(is_transient_diagnosis({
            "diagnosis": {
                "llm_input_tokens": 10,
                "status": "UNKNOWN",
                "reason_code": "invalid_json",
            }
        }))

    def test_model_unknown_is_not_transient(self):
        self.assertFalse(is_transient_diagnosis({
            "diagnosis": {
                "llm_input_tokens": 10,
                "status": "UNKNOWN",
                "reason_code": "model_unknown",
            }
        }))

    def test_valid_diagnosis_is_not_transient(self):
        self.assertFalse(is_transient_diagnosis({
            "diagnosis": {
                "llm_input_tokens": 10,
                "status": "ROOT_CAUSE_FOUND",
                "root_cause": "slow_sql",
            }
        }))


class RetryableExceptionTest(unittest.TestCase):
    def test_http_error_classification(self):
        self.assertTrue(is_retryable_exception(
            urllib.error.HTTPError("http://x", 503, "busy", {}, None)))
        self.assertTrue(is_retryable_exception(
            urllib.error.HTTPError("http://x", 429, "slow down", {}, None)))
        self.assertFalse(is_retryable_exception(
            urllib.error.HTTPError("http://x", 400, "bad", {}, None)))
        self.assertFalse(is_retryable_exception(
            urllib.error.HTTPError("http://x", 500, "bug", {}, None)))

    def test_network_and_explicit_transient(self):
        self.assertTrue(is_retryable_exception(urllib.error.URLError("reset")))
        self.assertTrue(is_retryable_exception(ConnectionResetError("reset")))
        self.assertTrue(is_retryable_exception(TransientE2EError("retry me")))


class RetryDecoratorTest(unittest.TestCase):
    def _run(self, fn, env_retries="1"):
        dummy = Dummy()
        with patch.dict(os.environ, {
            "E2E_RETRIES": env_retries,
            "E2E_RETRY_DELAY_SECONDS": "0",
        }), patch("tests.e2e.retry.time.sleep"):
            result = fn(dummy)
        return dummy, result

    def test_transient_error_is_retried_then_succeeds(self):
        @retry_transient
        def flaky(self):
            self.calls += 1
            if self.calls == 1:
                raise TransientE2EError("connection reset")
            return "ok"

        dummy, result = self._run(flaky)

        self.assertEqual(result, "ok")
        self.assertEqual(dummy.calls, 2)
        self.assertEqual(dummy.resets, 1)

    def test_http_503_is_retried(self):
        @retry_transient
        def flaky(self):
            self.calls += 1
            if self.calls == 1:
                raise urllib.error.HTTPError("http://x", 503, "busy", {}, None)
            return "ok"

        dummy, result = self._run(flaky)

        self.assertEqual(result, "ok")
        self.assertEqual(dummy.calls, 2)

    def test_assertion_is_not_retried(self):
        dummy = Dummy()

        @retry_transient
        def wrong(self):
            self.calls += 1
            raise AssertionError("wrong root cause")

        with patch.dict(os.environ, {"E2E_RETRIES": "2",
                                     "E2E_RETRY_DELAY_SECONDS": "0"}), \
                patch("tests.e2e.retry.time.sleep"), \
                self.assertRaises(AssertionError):
            wrong(dummy)
        self.assertEqual(dummy.calls, 1)

    def test_http_400_is_not_retried(self):
        dummy = Dummy()

        @retry_transient
        def bad_request(self):
            self.calls += 1
            raise urllib.error.HTTPError("http://x", 400, "bad", {}, None)

        with patch.dict(os.environ, {"E2E_RETRIES": "2",
                                     "E2E_RETRY_DELAY_SECONDS": "0"}), \
                patch("tests.e2e.retry.time.sleep"), \
                self.assertRaises(urllib.error.HTTPError):
            bad_request(dummy)

        self.assertEqual(dummy.calls, 1)


if __name__ == "__main__":
    unittest.main()
