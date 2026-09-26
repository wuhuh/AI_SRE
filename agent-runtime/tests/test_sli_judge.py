"""文档《独立修订版》11.5「一张必须通过的验证表」的直接翻译。

零流量不能当健康证据：无数据/NaN/Inf/负值/样本不足 → UNKNOWN；
明确超标或探测失败 → NOT_RECOVERED。
"""
import unittest

from app.agent.sli_verify import judge


class SliJudgeTest(unittest.TestCase):
    def test_sufficient_traffic_and_healthy(self):
        self.assertEqual(judge(0.001, 0.4), "RECOVERED")
        self.assertEqual(judge(0.0, 0.2, requests=1000), "RECOVERED")

    def test_error_rate_over_threshold(self):
        self.assertEqual(judge(0.5, 0.4), "NOT_RECOVERED")

    def test_latency_over_threshold(self):
        self.assertEqual(judge(0.0, 5.0), "NOT_RECOVERED")

    def test_missing_data_is_unknown(self):
        self.assertEqual(judge(None, None), "UNKNOWN")
        self.assertEqual(judge(0.001, None), "UNKNOWN")
        self.assertEqual(judge(None, 0.4), "UNKNOWN")

    def test_nan_and_inf_are_unknown_not_recovered(self):
        # 回归：NaN <= 阈值 恒为 False，旧实现把 NaN 判成 NOT_RECOVERED
        self.assertEqual(judge(float("nan"), 0.4), "UNKNOWN")
        self.assertEqual(judge(0.001, float("nan")), "UNKNOWN")
        self.assertEqual(judge(float("inf"), 0.4), "UNKNOWN")

    def test_negative_values_are_unknown(self):
        self.assertEqual(judge(-0.01, 0.4), "UNKNOWN")
        self.assertEqual(judge(0.001, -1.0), "UNKNOWN")

    def test_zero_traffic_is_unknown_even_without_errors(self):
        # 文档 11.3 情形 B：0 次请求不能从请求成功率证明服务可用
        self.assertEqual(judge(0.0, 0.2, requests=0), "UNKNOWN")
        # 情形 C：样本不足同样 UNKNOWN
        self.assertEqual(judge(0.0, 0.2, requests=50), "UNKNOWN")

    def test_custom_min_requests(self):
        self.assertEqual(judge(0.0, 0.2, requests=50, min_req=10), "RECOVERED")

    def test_invalid_config_raises(self):
        with self.assertRaises(ValueError):
            judge(0.0, 0.2, max_error=1.5)
        with self.assertRaises(ValueError):
            judge(0.0, 0.2, max_p95=-1)
        with self.assertRaises(ValueError):
            judge(0.0, 0.2, min_req=0)


if __name__ == "__main__":
    unittest.main()
