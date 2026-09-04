"""P0-03: 评测 runner 的离线单测（打分/输入构造/泄漏防护）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))

from run_evaluation import (  # noqa: E402
    ALERT_PROFILES,
    build_alert,
    evidence_scores,
    normalize_label,
    score,
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
        diagnosis = {"root_cause": "redis_connection_pool_exhausted",
                     "candidate_root_causes": ["redis_connection_pool_exhausted"]}
        self.assertEqual(score(diagnosis, "Redis connection pool is exhausted causing timeouts"), (False, False))

    def test_unknown_never_matches(self):
        self.assertEqual(score({"root_cause": "unknown", "candidate_root_causes": []}, "slow_sql"), (False, False))


class EvidenceScoresTest(unittest.TestCase):
    def test_precision_and_recall(self):
        diagnosis = {"evidence": [
            {"key": "redis_connection_usage_high"},
            {"key": "redis_timeout_log"},
            {"key": "noise_key"},
        ]}
        precision, recall = evidence_scores(diagnosis, {"expected_evidence": [
            "redis_connection_usage_high", "redis_timeout_log", "redis_span_latency_high"]})
        self.assertEqual(precision, round(2 / 3, 4))
        self.assertEqual(recall, round(2 / 3, 4))

    def test_no_expected_returns_none(self):
        self.assertEqual(evidence_scores({"evidence": []}, {"expected_evidence": []}), (None, None))


class SummarizeTest(unittest.TestCase):
    def test_report_math(self):
        rows = [
            {"top1": True, "top3": True, "fallback_used": False, "status": "ROOT_CAUSE_FOUND",
             "predicted": "slow_sql", "evidence_precision": 0.5, "evidence_recall": 1.0,
             "tool_calls": 2, "tool_success": 2, "llm_input_tokens": 10, "llm_output_tokens": 5,
             "latency_s": 1.0},
            {"top1": False, "top3": False, "fallback_used": True, "status": "UNKNOWN",
             "predicted": "unknown", "evidence_precision": None, "evidence_recall": None,
             "tool_calls": 0, "tool_success": 0, "llm_input_tokens": 0, "llm_output_tokens": 0,
             "latency_s": 3.0},
        ]
        report = summarize(rows)
        self.assertEqual(report["total_cases"], 2)
        self.assertEqual(report["root_cause_top1_accuracy"], 0.5)
        self.assertEqual(report["root_cause_top3_accuracy"], 0.5)
        self.assertEqual(report["unknown_rate"], 0.5)
        self.assertEqual(report["fallback_rate"], 0.5)
        self.assertEqual(report["evidence_recall_avg"], 1.0)
        self.assertEqual(report["tool_success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
