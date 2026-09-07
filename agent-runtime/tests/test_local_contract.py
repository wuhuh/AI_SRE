"""Contract test against the local lightweight API servers.

This validates that the API contract used by the E2E tests is stable:
alert ingestion returns incident id, agent diagnosis returns structured result,
and incident detail/evidence/tool-call endpoints return the expected shapes.
"""
from __future__ import annotations

import importlib.util
import json
import time
import unittest
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "e2e" / "local_contract_smoke.py"

spec = importlib.util.spec_from_file_location("local_contract_smoke", RUNNER_PATH)
local_e2e = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(local_e2e)


def request(method: str, url: str, payload: dict | None = None, timeout: float = 5):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


class LocalContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.servers = [
            local_e2e.start_server(local_e2e.CP_PORT, local_e2e.ControlPlaneHandler),
            local_e2e.start_server(local_e2e.AR_PORT, local_e2e.AgentRuntimeHandler),
            local_e2e.start_server(local_e2e.PAYMENT_PORT, local_e2e.PaymentHandler),
            local_e2e.start_server(local_e2e.INVENTORY_PORT, local_e2e.InventoryHandler),
        ]
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()

    def test_alert_contract(self):
        status, body = request("POST", f"http://localhost:{local_e2e.CP_PORT}/api/v1/alerts", {
            "service": "payment-service",
            "alertName": "contract_test",
            "resource": "payment-contract",
            "severity": "P1",
            "summary": "contract test alert",
        })
        self.assertEqual(status, 202)
        self.assertIn("incidentId", body)
        self.assertIn("duplicate", body)

    def test_diagnose_contract(self):
        status, alert_body = request("POST", f"http://localhost:{local_e2e.CP_PORT}/api/v1/alerts", {
            "service": "payment-service",
            "alertName": "contract_diag",
            "resource": "payment-contract-diag",
            "severity": "P1",
            "summary": "contract diag",
        })
        incident_id = alert_body["incidentId"]
        status, diag = request("POST", f"http://localhost:{local_e2e.AR_PORT}/api/v1/agent/diagnose", {
            "incident_id": incident_id,
            "alert": {"service": "payment-service", "summary": "contract diag"},
        }, timeout=10)
        self.assertEqual(status, 200)
        self.assertIn("root_cause", diag["diagnosis"])
        self.assertIsInstance(diag["diagnosis"]["tool_calls"], list)
        self.assertTrue(hasattr(diag["diagnosis"]["tool_calls"], "__len__"))

    def test_incident_detail_contract(self):
        status, alert_body = request("POST", f"http://localhost:{local_e2e.CP_PORT}/api/v1/alerts", {
            "service": "inventory-service",
            "alertName": "contract_detail",
            "resource": "inventory-contract",
            "severity": "P1",
            "summary": "contract detail",
        })
        incident_id = alert_body["incidentId"]
        status, incident = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/incidents/{incident_id}")
        self.assertEqual(status, 200)
        self.assertEqual(incident["id"], incident_id)
        self.assertIn("status", incident)
        self.assertIn("service", incident)
        status, evidence = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/incidents/{incident_id}/evidence")
        self.assertEqual(status, 200)
        self.assertIsInstance(evidence, list)
        status, tool_calls = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/incidents/{incident_id}/tool-calls")
        self.assertEqual(status, 200)
        self.assertIsInstance(tool_calls, list)
        status, audit_logs = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/incidents/{incident_id}/audit-logs")
        self.assertEqual(status, 200)
        self.assertIsInstance(audit_logs, list)
        status, report = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/incidents/{incident_id}/report")
        self.assertEqual(status, 200)
        self.assertIn("report", report)

    def test_task_pending_contract(self):
        status, alert_body = request("POST", f"http://localhost:{local_e2e.CP_PORT}/api/v1/alerts", {
            "service": "payment-service",
            "alertName": "task_contract",
            "resource": "payment-task",
            "severity": "P1",
            "summary": "task contract",
        })
        incident_id = alert_body["incidentId"]
        status, tasks = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/tasks/pending")
        self.assertEqual(status, 200)
        self.assertTrue(any(t["incidentId"] == incident_id for t in tasks))
        task = next(t for t in tasks if t["incidentId"] == incident_id)
        status, completed = request("POST", f"http://localhost:{local_e2e.CP_PORT}/api/v1/tasks/{task['id']}/complete", {})
        self.assertEqual(status, 200)
        self.assertEqual(completed["status"], "COMPLETED")

    def test_dashboard_summary_contract(self):
        status, summary = request("GET", f"http://localhost:{local_e2e.CP_PORT}/api/v1/dashboard/summary")
        self.assertEqual(status, 200)
        self.assertIn("total", summary)
        self.assertIn("resolved", summary)
        self.assertIn("diagnosing", summary)
        self.assertIn("failed", summary)


if __name__ == "__main__":
    unittest.main()
