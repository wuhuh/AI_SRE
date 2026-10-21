"""查询安全：告警 label 来自 webhook，不能直接拼进 PromQL / LogQL。

覆盖：
- 双引号/反斜杠被转义，不能闭合标签值；
- 换行被压平；
- Prometheus/LogTool 的真实查询构造都经过同一转义。
"""
from __future__ import annotations

import unittest
import urllib.parse
from unittest.mock import patch

from app.agent.diagnostic import prom_error_query, prom_latency_query
from app.tools.builtin_tools import LogTool
from app.tools.policy import escape_label_value


class LabelEscapeTest(unittest.TestCase):
    def test_quotes_and_backslashes_are_escaped(self):
        raw = 'payment" or vector(1) or "\\'
        escaped = escape_label_value(raw)
        self.assertIn('\\"', escaped)
        self.assertIn("\\\\", escaped)
        self.assertNotIn("\n", escape_label_value("a\nb"))

    def test_promql_cannot_be_closed_by_service_label(self):
        query = prom_error_query('payment" or vector(1) or "')
        self.assertIn('service="payment\\" or vector(1) or \\""', query)
        self.assertNotIn('service="payment" or vector(1)', query)

        latency = prom_latency_query('order"}}[1m] or vector(1) #')
        self.assertIn('\\"', latency)
        self.assertNotIn('service="order"}}', latency)


class LogQueryEscapeTest(unittest.TestCase):
    def test_logql_service_and_keyword_are_escaped(self):
        captured = {}

        def fake_get(url, timeout=3.0):
            captured["url"] = url
            return {}

        with patch("app.tools.builtin_tools._http_get_json", fake_get):
            LogTool("http://loki").execute({
                "service": 'pay"ment',
                "keyword": 'a"b',
                "traceId": 't"1',
            })

        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(captured["url"]).query)["query"][0]
        self.assertIn('service="pay\\"ment"', query)
        self.assertIn('|= "a\\"b"', query)
        self.assertIn('|= "t\\"1"', query)


if __name__ == "__main__":
    unittest.main()
