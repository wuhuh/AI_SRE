"""P0-03: 评测 runner 的离线单测（打分/输入构造/泄漏防护）。"""

from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))

from run_evaluation import (  # noqa: E402
    ALERT_PROFILES,
    _is_retryable_exception,
    _is_transient_diagnosis,
    build_alert,
    canonicalize_label,
    evaluate,
    evidence_scores,
    score,
    score_open,
    summarize,
)

TEN_FAULTS = [
    "cpu_saturation",
    "database_connection_pool_exhausted",
    "downstream_http_timeout",
    "memory_leak",
    "pod_crashloopbackoff",
    "redis_connection_pool_exhausted",
    "redis_slow_command",
    "rocketmq_message_backlog",
    "slow_sql",
    "thread_pool_exhausted",
]


class BuildAlertTest(unittest.TestCase):
    def test_every_fault_has_a_profile(self):
        self.assertEqual(set(ALERT_PROFILES), set(TEN_FAULTS))

    def test_fault_type_never_enters_the_alert(self):
        for fault in TEN_FAULTS:
            alert = build_alert({"fault_type": fault, "service": "order-service"})
            text = f"{alert['alertName']} {alert['summary']}".lower()
            self.assertNotIn(fault, text, f"fault_type leaked into alert for {fault}")
            self.assertNotIn("fault", text)

    def test_unknown_fault_rejected_loudly(self):
        with self.assertRaises(KeyError):
            build_alert({"fault_type": "martian_invasion", "service": "x"})

    def test_unknown_profile_is_neutral_and_dedicated(self):
        alert = build_alert({"id": "unknown_001", "fault_type": "unknown",
                             "service": "payment-service"})
        text = f"{alert['alertName']} {alert['summary']}".lower()
        self.assertNotIn("fault", text)
        self.assertNotIn("unknown", text)


class OpenSetScoringTest(unittest.TestCase):
    def test_free_form_label_is_canonicalized(self):
        self.assertEqual(canonicalize_label("Redis Pool Exhausted"),
                         "redis_connection_pool_exhausted")
        self.assertEqual(canonicalize_label("db_pool_exhausted"),
                         "database_connection_pool_exhausted")
        self.assertEqual(canonicalize_label("unknown"), "unknown")
        self.assertEqual(canonicalize_label("network_policy_misconfiguration"),
                         "network_policy_misconfiguration")

    def test_open_score_matches_synonyms(self):
        diagnosis = {
            "root_cause": "Redis Pool Exhausted",
            "candidate_root_causes": ["Redis Pool Exhausted"],
        }
        self.assertEqual(
            score_open(diagnosis, "redis_connection_pool_exhausted"), (True, True))

    def test_open_score_unknown_expected_requires_abstention(self):
        abstain = {"root_cause": "unknown", "candidate_root_causes": ["unknown"]}
        guess = {"root_cause": "slow_sql", "candidate_root_causes": ["slow_sql"]}
        self.assertEqual(score_open(abstain, "unknown"), (True, True))
        self.assertEqual(score_open(guess, "unknown"), (False, False))

    def test_open_score_unknown_is_not_a_match_for_known_expected(self):
        abstain = {"root_cause": "unknown", "candidate_root_causes": []}
        self.assertEqual(score_open(abstain, "slow_sql"), (False, False))

    def test_open_top1_uses_primary_not_first_candidate(self):
        # 主结论 unknown、候选里有正确答案：仍必须算拒答，不能虚高 Top-1。
        abstain_with_alternative = {
            "root_cause": "unknown",
            "candidate_root_causes": ["slow_sql"],
        }
        self.assertEqual(score_open(abstain_with_alternative, "slow_sql"), (False, False))
        self.assertEqual(score(abstain_with_alternative, "slow_sql"), (False, False))


class ScoreTest(unittest.TestCase):
    def test_top1_exact_match(self):
        diagnosis = {"root_cause": "Slow SQL", "candidate_root_causes": ["Slow SQL"]}
        self.assertEqual(score(diagnosis, "slow_sql"), (True, True))

    def test_top3_uses_real_candidates(self):
        diagnosis = {
            "root_cause": "memory_leak",
            "candidate_root_causes": ["memory_leak", "cpu_saturation", "thread_pool_exhausted"],
        }
        self.assertEqual(score(diagnosis, "cpu_saturation"), (False, True))

    def test_top3_misses_beyond_three(self):
        diagnosis = {
            "root_cause": "memory_leak",
            "candidate_root_causes": ["memory_leak", "cpu_saturation", "thread_pool_exhausted"],
        }
        self.assertEqual(score(diagnosis, "slow_sql"), (False, False))

    def test_old_bidirectional_substring_bug_is_gone(self):
        # 旧打分逻辑把 "redis_connection_pool_exhausted" 与自然语言期望句判为命中；
        # 新逻辑（精确标签匹配）必须判为不中。
        diagnosis = {
            "root_cause": "redis_connection_pool_exhausted",
            "candidate_root_causes": ["redis_connection_pool_exhausted"],
        }
        self.assertEqual(score(diagnosis, "Redis connection pool is exhausted causing timeouts"), (False, False))

    def test_unknown_never_matches(self):
        self.assertEqual(score({"root_cause": "unknown", "candidate_root_causes": []}, "slow_sql"), (False, False))


class EvidenceScoresTest(unittest.TestCase):
    def test_tag_matches_key_source_and_content(self):
        # P2-FI-10: 产出 key 是 tool:step 序号 —— 语义标签要在 key/source/content 上按词匹配
        diagnosis = {
            "evidence": [
                {
                    "key": "query_prometheus:3",
                    "source": "prometheus",
                    "content": "used_connections==maxclients redis pool exhausted",
                },
                {"key": "query_logs:2", "source": "logs", "content": "slowlog latency 120ms on redis"},
                {"key": "query_trace:1", "source": "trace", "content": "span latency high"},
            ]
        }
        precision, recall = evidence_scores(
            diagnosis, {"expected_evidence": ["redis_pool_exhausted", "redis_slowlog", "span_latency_high"]}
        )
        self.assertEqual(recall, 1.0)
        self.assertEqual(precision, 1.0)

    def test_partial_recall_and_noise(self):
        diagnosis = {
            "evidence": [
                {"key": "query_logs:1", "source": "logs", "content": "unrelated text"},
            ]
        }
        precision, recall = evidence_scores(diagnosis, {"expected_evidence": ["redis_slowlog", "cpu_high"]})
        self.assertEqual(recall, 0.0)
        self.assertEqual(precision, 0.0)

    def test_no_expected_returns_none(self):
        self.assertEqual(evidence_scores({"evidence": []}, {"expected_evidence": []}), (None, None))


class SummarizeTest(unittest.TestCase):
    def test_report_math(self):
        rows = [
            {
                "top1": True,
                "top3": True,
                "fallback_used": False,
                "status": "ROOT_CAUSE_FOUND",
                "predicted": "slow_sql",
                "evidence_precision": 0.5,
                "evidence_recall": 1.0,
                "tool_calls": 2,
                "tool_success": 2,
                "llm_input_tokens": 10,
                "llm_output_tokens": 5,
                "latency_s": 1.0,
            },
            {
                "top1": False,
                "top3": False,
                "fallback_used": True,
                "status": "UNKNOWN",
                "predicted": "unknown",
                "evidence_precision": None,
                "evidence_recall": None,
                "tool_calls": 0,
                "tool_success": 0,
                "llm_input_tokens": 0,
                "llm_output_tokens": 0,
                "latency_s": 3.0,
            },
        ]
        report = summarize(rows)
        self.assertEqual(report["total_cases"], 2)
        self.assertEqual(report["root_cause_top1_accuracy"], 0.5)
        self.assertEqual(report["root_cause_top3_accuracy"], 0.5)
        self.assertEqual(report["unknown_rate"], 0.5)
        self.assertEqual(report["fallback_rate"], 0.5)
        self.assertEqual(report["llm_error_cases"], 1)
        self.assertEqual(report["evidence_recall_avg"], 1.0)
        self.assertEqual(report["tool_success_rate"], 1.0)

    def test_open_set_metrics_separate_abstention_from_accuracy(self):
        def row(expected, predicted, status, top1, top3):
            return {
                "expected": expected,
                "predicted": predicted,
                "predicted_canonical": predicted,
                "top1": top1,
                "top3": top3,
                "status": status,
                "fallback_used": status == "UNKNOWN",
                "evidence_precision": None,
                "evidence_recall": None,
                "tool_calls": 0,
                "tool_success": 0,
                "llm_input_tokens": 0,
                "llm_output_tokens": 0,
                "latency_s": 1.0,
            }

        rows = [
            row("slow_sql", "slow_sql", "ROOT_CAUSE_FOUND", True, True),
            row("cpu_saturation", "memory_leak", "ROOT_CAUSE_FOUND", False, False),
            row("unknown", "unknown", "UNKNOWN", True, True),
            row("unknown", "slow_sql", "ROOT_CAUSE_FOUND", False, False),
        ]
        report = summarize(rows, open_set=True)

        self.assertEqual(report["known_case_count"], 2)
        self.assertEqual(report["known_case_top1_accuracy"], 0.5)
        self.assertEqual(report["unknown_case_count"], 2)
        self.assertEqual(report["unknown_case_abstention_accuracy"], 0.5)
        self.assertEqual(report["answered_cases"], 3)
        self.assertEqual(report["coverage"], 0.75)
        self.assertEqual(report["selective_top1_accuracy"], 0.3333)
        self.assertEqual(report["wrong_confident_rate"], 0.5)
        self.assertEqual(report["mode"], "open")


def _diagnosis(root: str, tokens: int, status: str = "ROOT_CAUSE_FOUND") -> dict:
    return {
        "diagnosis": {
            "root_cause": root,
            "candidate_root_causes": [root] if root != "unknown" else [],
            "confidence": 0.8,
            "status": status,
            "fallback_used": status == "UNKNOWN",
            "tool_calls": [],
            "evidence": [],
            "llm_input_tokens": tokens,
            "llm_output_tokens": 5,
        }
    }


RETRY_CASE = {"id": "retry_case", "fault_type": "slow_sql", "service": "payment-service"}


class EvaluationRetryTest(unittest.TestCase):
    def test_retryable_exception_classification(self):
        self.assertTrue(_is_retryable_exception(ConnectionResetError("reset")))
        self.assertTrue(_is_retryable_exception(urllib.error.URLError("reset")))
        self.assertTrue(_is_retryable_exception(
            urllib.error.HTTPError("http://x", 503, "busy", {}, None)))
        self.assertFalse(_is_retryable_exception(
            urllib.error.HTTPError("http://x", 400, "bad request", {}, None)))
        # 500 可能是代码 bug，不重试，避免掩盖问题
        self.assertFalse(_is_retryable_exception(
            urllib.error.HTTPError("http://x", 500, "bug", {}, None)))

    def test_transient_diagnosis_is_zero_token_only(self):
        self.assertTrue(_is_transient_diagnosis({"llm_input_tokens": 0, "status": "UNKNOWN"}))
        self.assertFalse(_is_transient_diagnosis({
            "llm_input_tokens": 10, "status": "UNKNOWN", "reason_code": "model_unknown"}))

    def test_evaluate_retries_connection_reset(self):
        with patch("run_evaluation.call_diagnose",
                   side_effect=[ConnectionResetError("reset"), (_diagnosis("slow_sql", 10), 0.2)]) as call, \
                patch("run_evaluation.time.sleep"):
            rows = evaluate([RETRY_CASE], retries=1)

        self.assertEqual(call.call_count, 2)
        self.assertEqual(rows[0]["attempts"], 2)
        self.assertTrue(rows[0]["retried"])
        self.assertEqual(rows[0]["predicted"], "slow_sql")
        self.assertTrue(rows[0]["top1"])

    def test_evaluate_retries_zero_token_then_success(self):
        with patch("run_evaluation.call_diagnose",
                   side_effect=[(_diagnosis("unknown", 0, "UNKNOWN"), 0.1),
                                (_diagnosis("slow_sql", 10), 0.2)]) as call, \
                patch("run_evaluation.time.sleep"):
            rows = evaluate([RETRY_CASE], retries=1)

        self.assertEqual(call.call_count, 2)
        self.assertEqual(rows[0]["attempts"], 2)
        self.assertEqual(rows[0]["predicted"], "slow_sql")

    def test_evaluate_does_not_retry_model_unknown(self):
        with patch("run_evaluation.call_diagnose",
                   return_value=(_diagnosis("unknown", 10, "UNKNOWN"), 0.1)) as call, \
                patch("run_evaluation.time.sleep"):
            rows = evaluate([RETRY_CASE], retries=2)

        self.assertEqual(call.call_count, 1)
        self.assertEqual(rows[0]["attempts"], 1)
        self.assertFalse(rows[0]["retried"])

    def test_evaluate_does_not_retry_http_400(self):
        err = urllib.error.HTTPError("http://x", 400, "bad request", {}, None)
        with patch("run_evaluation.call_diagnose", side_effect=err) as call, \
                patch("run_evaluation.time.sleep"):
            rows = evaluate([RETRY_CASE], retries=2)

        self.assertEqual(call.call_count, 1)
        self.assertEqual(rows[0]["status"], "HTTP_ERROR")
        self.assertEqual(rows[0]["attempts"], 1)

    def test_summarize_reports_attempt_metrics(self):
        row = {
            "expected": "slow_sql",
            "predicted": "slow_sql",
            "predicted_canonical": "slow_sql",
            "top1": True,
            "top3": True,
            "status": "ROOT_CAUSE_FOUND",
            "fallback_used": False,
            "evidence_precision": None,
            "evidence_recall": None,
            "tool_calls": 0,
            "tool_success": 0,
            "llm_input_tokens": 10,
            "llm_output_tokens": 5,
            "latency_s": 0.2,
            "attempts": 2,
            "retried": True,
        }
        report = summarize([row])
        self.assertEqual(report["retried_cases"], 1)
        self.assertEqual(report["retry_successes"], 1)
        self.assertEqual(report["total_attempts"], 2)


if __name__ == "__main__":
    unittest.main()
