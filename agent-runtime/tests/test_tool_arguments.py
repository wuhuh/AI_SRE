"""P0-02: 工具参数必须由告警驱动（服务名 + 对齐 demo 指标的 PromQL），不得硬编码。"""
from __future__ import annotations

import unittest

from app.agent.diagnostic import DiagnosticAgent, prom_query_for
from app.agent.verification import VerificationAgent
from app.llm.mock import MockLLMProvider
from app.models import AgentState
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry


class RecordingTool(Tool):
    def __init__(self, name: str):
        self.spec = ToolSpec(
            name=name,
            description="recorder",
            parameters={"type": "object", "properties": {}, "required": []},
            risk_level="READ_ONLY",
        )
        self.seen: list[dict] = []

    def execute(self, arguments, principal="agent"):
        self.seen.append(arguments)
        return '{"status":"success"}'


def _registry_with_recorder() -> tuple[ToolRegistry, RecordingTool]:
    registry = ToolRegistry()
    recorder = RecordingTool("query_prometheus")
    registry.register(recorder)
    return registry, recorder


class DiagnosticToolArgumentsTest(unittest.TestCase):
    def test_prometheus_query_uses_alert_service(self):
        registry, recorder = _registry_with_recorder()
        agent = DiagnosticAgent(MockLLMProvider(), registry)
        alert = {"service": "inventory-service", "alertName": "HighErrorRate", "summary": "5xx spike"}
        state = AgentState(incident_id=1, alert=alert)
        state.plan = ["query_prometheus"]
        agent.run(state)
        self.assertEqual(len(recorder.seen), 1)
        query = recorder.seen[0]["query"]
        self.assertIn('service="inventory-service"', query)
        self.assertIn("http_requests_total", query)
        self.assertIn('status=~"5.."', query)

    def test_latency_alert_uses_histogram_query(self):
        registry, recorder = _registry_with_recorder()
        agent = DiagnosticAgent(MockLLMProvider(), registry)
        alert = {"service": "order-service", "alertName": "HighLatency", "summary": "p99 high"}
        state = AgentState(incident_id=2, alert=alert)
        state.plan = ["query_prometheus"]
        agent.run(state)
        query = recorder.seen[0]["query"]
        self.assertIn("histogram_quantile", query)
        self.assertIn('service="order-service"', query)
        self.assertNotIn("http_server_requests_seconds_count", query)

    def test_missing_service_falls_back_to_marker(self):
        self.assertIn("unknown-service", prom_query_for({"summary": "5xx"}))


class VerificationToolArgumentsTest(unittest.TestCase):
    def test_verification_targets_alert_service(self):
        registry, recorder = _registry_with_recorder()
        agent = VerificationAgent(MockLLMProvider(), registry)
        state = AgentState(incident_id=3, alert={"service": "inventory-service"})
        agent.run(state)
        self.assertTrue(all('service="inventory-service"' in str(a) for a in recorder.seen))


if __name__ == "__main__":
    unittest.main()
