"""P0-04: tool-server 写操作必须 POST + X-Execution-Token 精确匹配；GET 只保留只读。"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("APPROVAL_TOKEN", "local-dev-token")

import app as tool_server  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(tool_server.app)
TOKEN = os.environ["APPROVAL_TOKEN"]
SCALE = {"action": "scale_deployment", "namespace": "prod", "deployment": "payment-service", "replicas": 5}


class WriteActionAuthTest(unittest.TestCase):
    def test_missing_token_rejected(self):
        self.assertEqual(client.post("/api/k8s", json=SCALE).status_code, 403)

    def test_wrong_token_rejected_even_if_long(self):
        # 旧实现 len>=8 即放行 —— 现在必须精确匹配
        r = client.post("/api/k8s", json=SCALE, headers={"X-Execution-Token": "x" * 16})
        self.assertEqual(r.status_code, 403)

    def test_correct_token_executes_dry_run(self):
        r = client.post("/api/k8s", json=SCALE, headers={"X-Execution-Token": TOKEN})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["dryRun"])
        self.assertEqual(body["params"]["replicas"], 5)
        self.assertEqual(body["namespace"], "prod")

    def test_write_via_get_is_rejected(self):
        self.assertEqual(client.get("/api/k8s?action=scale_deployment").status_code, 405)

    def test_read_actions_stay_open(self):
        self.assertEqual(client.get("/api/k8s?action=list_pods").status_code, 200)

    def test_unknown_action_rejected(self):
        r = client.post("/api/k8s", json={"action": "whatever"}, headers={"X-Execution-Token": TOKEN})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
