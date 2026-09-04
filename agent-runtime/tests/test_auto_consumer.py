import importlib.util
import json
import time
import unittest
import urllib.request
from pathlib import Path

from app.agent.runner import AgentRunner
from app.consumer import consume_once
from app.llm.mock import MockLLMProvider
from app.tools.registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "e2e" / "local_e2e_runner.py"

spec = importlib.util.spec_from_file_location("local_e2e_runner", RUNNER_PATH)
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


class AutoConsumerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cp_server = local_e2e.start_server(local_e2e.CP_PORT, local_e2e.ControlPlaneHandler)
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.cp_server.shutdown()
        cls.cp_server.server_close()

    def test_alert_task_is_consumed_and_diagnosed(self):
        cp_url = f"http://localhost:{local_e2e.CP_PORT}"
        request("POST", f"{cp_url}/api/v1/alerts", {
            "service": "payment-service",
            "alertName": "auto_consumer",
            "resource": "payment-auto",
            "severity": "P1",
            "summary": "payment latency high",
        })
        status, tasks = request("GET", f"{cp_url}/api/v1/tasks/pending")
        self.assertEqual(status, 200)
        self.assertTrue(tasks)

        runner = AgentRunner(llm=MockLLMProvider(), registry=ToolRegistry(), retriever=None)
        processed = consume_once(runner, cp_url)
        self.assertGreaterEqual(processed, 1)

        status, tasks_after = request("GET", f"{cp_url}/api/v1/tasks/pending")
        self.assertEqual(tasks_after, [])
        incident_id = tasks[0]["incidentId"]
        status, incident = request("GET", f"{cp_url}/api/v1/incidents/{incident_id}")
        self.assertEqual(status, 200)
        self.assertIsNotNone(incident.get("rootCause"))

    def test_claim_prevents_duplicate_consumption(self):
        # P1-MQ-02: 任务被副本 A 领走后，副本 B 的 consume_once 必须跳过（不重复诊断）
        cp_url = f"http://localhost:{local_e2e.CP_PORT}"
        request("POST", f"{cp_url}/api/v1/alerts", {
            "service": "order-service",
            "alertName": "claim_test",
            "resource": "order-claim",
            "severity": "P2",
            "summary": "order latency high",
        })
        status, tasks = request("GET", f"{cp_url}/api/v1/tasks/pending")
        self.assertTrue(tasks)
        task_id = tasks[0]["id"]
        incident_id = tasks[0]["incidentId"]

        # 副本 A 抢走任务
        status, claim = request("POST", f"{cp_url}/api/v1/tasks/{task_id}/claim", {"worker": "replica-a"})
        self.assertEqual(status, 200)
        self.assertTrue(claim["claimed"])

        # 副本 B 消费：claim 失败 → 跳过，不产生诊断
        runner = AgentRunner(llm=MockLLMProvider(), registry=ToolRegistry(), retriever=None)
        self.assertEqual(consume_once(runner, cp_url), 0)
        _, incident = request("GET", f"{cp_url}/api/v1/incidents/{incident_id}")
        self.assertIsNone(incident.get("rootCause"))

        # 副本 A 正常完成后任务离队
        request("POST", f"{cp_url}/api/v1/tasks/{task_id}/complete", {})
        self.assertEqual(consume_once(runner, cp_url), 0)


if __name__ == "__main__":
    unittest.main()