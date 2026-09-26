"""文档 7.6：外部动作 execution_id 幂等。

重复 execution_id 不再真实执行第二次：已完成的返回已知结果，
IN_FLIGHT（执行中/响应丢失）返回 UNKNOWN 待对账。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APPROVAL_TOKEN", "local-dev-token")

import app as tool_server  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TOKEN = os.environ["APPROVAL_TOKEN"]


class ExecutionIdempotencyTest(unittest.TestCase):
    def setUp(self):
        # 每个用例独立的操作记录文件，避免互相污染
        self.tmp = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self.tmp.name, "operations.json")
        tool_server.OPERATIONS = tool_server.OperationStore(self.log_path)
        self.client = TestClient(tool_server.app)

    def tearDown(self):
        self.tmp.cleanup()

    def _post(self, execution_id):
        return self.client.post(
            "/api/k8s",
            json={"action": "scale_deployment", "namespace": "prod",
                  "deployment": "payment-service", "replicas": 5,
                  "execution_id": execution_id},
            headers={"X-Execution-Token": TOKEN},
        )

    def test_first_call_records_operation(self):
        r = self._post("rem-100")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["dryRun"])
        stored = tool_server.OPERATIONS.lookup("rem-100")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["status"], "NOT_EXECUTED")

    def test_duplicate_returns_recorded_result_without_reexecution(self):
        self._post("rem-101")
        r2 = self._post("rem-101")
        body = r2.json()
        self.assertTrue(body["duplicate"])
        self.assertEqual(body["status"], "NOT_EXECUTED")

    def test_in_flight_returns_unknown_for_reconciliation(self):
        # 模拟「执行后、记录结果前进程崩溃」：意图已记录，结果缺失
        tool_server.OPERATIONS.record("rem-102", {"action": "restart_pod", "status": "IN_FLIGHT"})
        r = self._post("rem-102")
        body = r.json()
        self.assertTrue(body["duplicate"])
        self.assertEqual(body["status"], "UNKNOWN")
        self.assertIn("reconciliation", body["detail"])

    def test_missing_execution_id_keeps_legacy_behavior(self):
        r = self.client.post(
            "/api/k8s",
            json={"action": "scale_deployment", "namespace": "prod",
                  "deployment": "payment-service", "replicas": 5},
            headers={"X-Execution-Token": TOKEN},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["dryRun"])
        # 无 execution_id 的请求不留操作记录（无法做幂等键）
        self.assertEqual(tool_server.OPERATIONS._load(), {})

    def test_different_ids_execute_independently(self):
        self._post("rem-201")
        r = self._post("rem-202")
        self.assertNotIn("duplicate", r.json())


if __name__ == "__main__":
    unittest.main()
