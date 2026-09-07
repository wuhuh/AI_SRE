"""Real-environment E2E fault tests.

These tests require the Docker Compose environment to be running:
    docker compose up -d --build

They inject real faults into demo services, send real alerts to Control Plane,
call the real Agent Runtime, and verify service recovery after disabling the fault.

If services are not reachable, the tests are skipped so local unit test runs
remain fast and offline.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CP_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:8080").rstrip("/")
AR_URL = os.getenv("AGENT_URL", "http://localhost:8081").rstrip("/")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://localhost:8001").rstrip("/")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:8003").rstrip("/")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "local-dev-agent-token")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "local-dev-webhook-token")
JWT_TOKEN = os.getenv("JWT_TOKEN", "")  # P0-05 后 CP 只读端点也要 JWT


def _login_jwt() -> str:
    """admin 登录取 JWT（compose 默认 aisre-dev-admin-pw；可用 JWT_TOKEN 直给）。"""
    global JWT_TOKEN
    if JWT_TOKEN:
        return JWT_TOKEN
    status, body = request("POST", f"{CP_URL}/api/v1/auth/login", {
        "username": os.getenv("ADMIN_USER", "admin"),
        "password": os.getenv("ADMIN_PASSWORD", "aisre-dev-admin-pw"),
    })
    if status == 200:
        JWT_TOKEN = body.get("token", "")
    return JWT_TOKEN

# P3-T-06: 诊断内容断言 —— root_cause 必须落在故障的期望标签集合内。
# mock LLM 恒答 redis（AR-12 同源问题，已文档披露）：非 mock 时才做严格集合断言。
EXPECTED_ROOT_CAUSES = {
    "redis_pool_exhausted": {"redis_connection_pool_exhausted", "redis_pool_exhausted"},
    "slow_sql": {"slow_sql", "database_slow_query", "slow_database_query"},
    "cpu_saturation": {"cpu_saturation", "container_cpu_saturation", "high_cpu"},
}


def _assert_root_cause(testcase, diag, fault_type: str) -> None:
    root = (diag["diagnosis"].get("root_cause") or "").strip().lower()
    testcase.assertTrue(root, "diagnosis must produce a root_cause label")
    if os.getenv("LLM_PROVIDER", "mock") == "mock":
        # mock 与 case 期望同源：只能断言「非 unknown 的规范标签」，不冒充真实能力
        testcase.assertNotEqual(root, "unknown")
        return
    testcase.assertIn(root, EXPECTED_ROOT_CAUSES[fault_type],
                      f"root_cause {root!r} not in expected set for {fault_type}")


def _assert_recovery_faster(testcase, slow_duration: float, recovered_duration: float) -> None:
    """P3-T-06: 恢复断言改比例阈值（绝对秒数对负载/CI 波动 flaky）。"""
    testcase.assertEqual(True, recovered_duration < slow_duration)
    testcase.assertGreaterEqual(
        slow_duration, recovered_duration * 3,
        f"faulted path {slow_duration:.2f}s should be >=3x slower than recovered {recovered_duration:.2f}s")


def request(method: str, url: str, payload: dict | None = None, timeout: float = 10.0,
            headers: dict | None = None, auth: bool = True):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    base_headers = {"Content-Type": "application/json"} if data else {}
    # P0-05: CP 只读端点需 JWT（agent 端点用 X-Agent-Token，webhook 用 X-Webhook-Token）
    if auth and "8080" in url and "auth/login" not in url and JWT_TOKEN:
        base_headers["Authorization"] = f"Bearer {JWT_TOKEN}"
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={**base_headers, **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def log(msg: str) -> None:
    print(f"[E2E] {msg}", flush=True)


def wait_until(predicate, timeout: float = 20.0, interval: float = 1.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # noqa: BLE001 - E2E helper
            last = exc
        time.sleep(interval)
    if last:
        raise last
    raise TimeoutError("wait_until timed out")


class RealFaultE2ETest(unittest.TestCase):

    @classmethod
    def _core_health_ok(cls) -> bool:
        try:
            request("GET", f"{CP_URL}/health", timeout=3)
            request("GET", f"{AR_URL}/health", timeout=3)
            return True
        except Exception:
            return False

    @classmethod
    def setUpClass(cls):
        if os.getenv("RUN_E2E", "0") != "1":
            raise unittest.SkipTest("Set RUN_E2E=1 to run real environment E2E tests")

        if not cls._core_health_ok():
            if os.getenv("SKIP_DOCKER_AUTOSTART", "0") == "1":
                raise RuntimeError("Core services not reachable; skip docker autostart is enabled")
            log("core services not reachable, trying to start docker compose...")
            try:
                result = subprocess.run(
                    ["docker", "compose", "up", "-d", "--build"],
                    cwd=str(PROJECT_ROOT),
                    timeout=180,
                    capture_output=True,
                    text=True,
                )
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"Failed to start Docker Compose: {exc}") from exc
            if result.returncode != 0:
                raise RuntimeError(f"Docker Compose failed:\n{result.stderr}")
            wait_until(cls._core_health_ok, timeout=120, interval=5)

        _login_jwt()
        for label, url in (("payment-service", PAYMENT_URL), ("inventory-service", INVENTORY_URL)):
            try:
                request("GET", f"{url}/health", timeout=3)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"{label} not reachable at {url}. Please run `docker compose up -d --build`. Detail: {exc}"
                ) from exc

    def _set_fault(self, service_url: str, name: str, enabled: bool) -> None:
        request("POST", f"{service_url}/faults?name={name}&enabled={str(enabled).lower()}", timeout=5)

    def _send_alert(self, service: str, resource: str, summary: str) -> int:
        status, body = request("POST", f"{CP_URL}/api/v1/alerts/alertmanager", {
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "labels": {
                        "service": service,
                        "alertname": "e2e_fault",
                        "resource": resource,
                        "severity": "P1",
                    },
                    "annotations": {"summary": summary},
                }
            ],
        }, headers={"X-Webhook-Token": WEBHOOK_TOKEN})
        self.assertEqual(status, 202)
        # v4 契约：{"results":[{"incidentId":...}],"skippedResolved":0}
        return body["results"][0]["incidentId"]

    def _diagnose(self, incident_id: int, service: str) -> dict:
        status, body = request("POST", f"{AR_URL}/api/v1/agent/diagnose", {
            "incident_id": incident_id,
            "alert": {
                "service": service,
                "alertName": "e2e_fault",
                "severity": "P1",
                "summary": f"{service} real fault injected for e2e",
            },
        # 诊断端到端含真实工具链路（Prom/Tempo/Loki），30s 贴边易超——对齐 DIAG_BUDGET
        }, timeout=180, headers={"X-Agent-Token": AGENT_TOKEN})
        self.assertEqual(status, 200)
        return body

    def _verify(self, incident_id: int, service: str) -> dict:
        status, body = request("POST", f"{AR_URL}/api/v1/agent/verify", {
            "incident_id": incident_id,
            "alert": {
                "service": service,
                "alertName": "e2e_fault",
                "severity": "P1",
                "summary": f"{service} real fault injected for e2e",
            },
        # 诊断端到端含真实工具链路（Prom/Tempo/Loki），30s 贴边易超——对齐 DIAG_BUDGET
        }, timeout=180, headers={"X-Agent-Token": AGENT_TOKEN})
        self.assertEqual(status, 200)
        return body

    def _incident_status(self, incident_id: int) -> str:
        _, body = request("GET", f"{CP_URL}/api/v1/incidents/{incident_id}")
        return body["status"]

    def test_redis_connection_pool_exhausted_real_fault(self):
        log("send alert for redis_pool_exhausted")
        incident_id = self._send_alert("payment-service", "payment-e2e-redis", "payment-service redis connection pool exhausted")

        log("inject redis_pool_exhausted fault")
        self._set_fault(PAYMENT_URL, "redis_pool_exhausted", True)
        try:
            # Generate real failing traffic.
            log("call /payments and expect 503")
            with self.assertRaises(urllib.error.HTTPError):
                request("POST", f"{PAYMENT_URL}/payments", {"amount": 1}, timeout=5)

            log("run agent diagnosis")
            diag = self._diagnose(incident_id, "payment-service")
            log(f"diagnosis root_cause={diag['diagnosis']['root_cause']}")
            _assert_root_cause(self, diag, "redis_pool_exhausted")
            self.assertGreater(len(diag["diagnosis"]["tool_calls"]), 0)

            # Real recovery: disable fault and verify the service is healthy again.
            log("disable redis_pool_exhausted fault")
            self._set_fault(PAYMENT_URL, "redis_pool_exhausted", False)
            log("verify /payments recovers to 200")
            ok = wait_until(lambda: request("POST", f"{PAYMENT_URL}/payments", {"amount": 1}, timeout=5)[0] == 200)
            self.assertTrue(ok)

            log("run agent verification")
            verification = self._verify(incident_id, "payment-service")
            log(f"verification status={verification['verification']['status']}")
            self.assertEqual(verification["verification"]["status"], "RECOVERED")
            log("wait incident resolved")
            wait_until(lambda: self._incident_status(incident_id) == "RESOLVED")
        finally:
            log("cleanup fault")
            self._set_fault(PAYMENT_URL, "redis_pool_exhausted", False)

    def test_slow_sql_real_fault(self):
        log("send alert for slow_sql")
        incident_id = self._send_alert("inventory-service", "inventory-e2e-slow-sql", "inventory-service slow sql")

        log("inject slow_sql fault")
        self._set_fault(INVENTORY_URL, "slow_sql", True)
        try:
            # Generate a request that hits the slow inventory path.
            log("call /inventory/check and measure slow duration")
            start = time.time()
            request("POST", f"{INVENTORY_URL}/inventory/check", {"items": ["sku-1"]}, timeout=10)
            slow_duration = time.time() - start
            log(f"slow_duration={slow_duration:.2f}s")
            self.assertGreaterEqual(slow_duration, 1.5)

            log("run agent diagnosis")
            diag = self._diagnose(incident_id, "inventory-service")
            log(f"diagnosis root_cause={diag['diagnosis']['root_cause']}")
            _assert_root_cause(self, diag, "slow_sql")
            self.assertGreater(len(diag["diagnosis"]["tool_calls"]), 0)

            # Real recovery: disable slow SQL fault.
            log("disable slow_sql fault")
            self._set_fault(INVENTORY_URL, "slow_sql", False)
            start = time.time()
            status, _ = request("POST", f"{INVENTORY_URL}/inventory/check", {"items": ["sku-1"]}, timeout=10)
            recovered_duration = time.time() - start
            log(f"recovered_duration={recovered_duration:.2f}s")
            self.assertEqual(status, 200)
            # The key signal is that the slow path is gone; local/CI socket overhead
            # can add a small constant delay, so compare against the faulted duration.
            _assert_recovery_faster(self, slow_duration, recovered_duration)

            log("run agent verification")
            verification = self._verify(incident_id, "inventory-service")
            log(f"verification status={verification['verification']['status']}")
            self.assertEqual(verification["verification"]["status"], "RECOVERED")
            log("wait incident resolved")
            wait_until(lambda: self._incident_status(incident_id) == "RESOLVED")
        finally:
            log("cleanup fault")
            self._set_fault(INVENTORY_URL, "slow_sql", False)

    def test_cpu_saturation_real_fault(self):
        log("send alert for cpu_saturation")
        incident_id = self._send_alert("inventory-service", "inventory-e2e-cpu-sat", "inventory-service cpu saturation")

        log("inject cpu_saturation fault")
        self._set_fault(INVENTORY_URL, "cpu_saturation", True)
        try:
            log("call /inventory/check while cpu saturated")
            start = time.time()
            request("POST", f"{INVENTORY_URL}/inventory/check", {"items": ["sku-1"]}, timeout=10)
            slow_duration = time.time() - start
            log(f"degraded_duration={slow_duration:.2f}s")
            # P3-T-06: cpu burn=0.6s（P0-08 真实化后非绝对 1.5s 延迟）——
            # 降级幅度由恢复后的比例断言（_assert_recovery_faster ≥3x）承担

            log("run agent diagnosis")
            diag = self._diagnose(incident_id, "inventory-service")
            log(f"diagnosis root_cause={diag['diagnosis']['root_cause']}")
            _assert_root_cause(self, diag, "cpu_saturation")
            self.assertGreater(len(diag["diagnosis"]["tool_calls"]), 0)

            log("disable cpu_saturation fault")
            self._set_fault(INVENTORY_URL, "cpu_saturation", False)
            start = time.time()
            status, _ = request("POST", f"{INVENTORY_URL}/inventory/check", {"items": ["sku-1"]}, timeout=10)
            recovered_duration = time.time() - start
            log(f"recovered_duration={recovered_duration:.2f}s")
            self.assertEqual(status, 200)
            _assert_recovery_faster(self, slow_duration, recovered_duration)

            log("run agent verification")
            verification = self._verify(incident_id, "inventory-service")
            log(f"verification status={verification['verification']['status']}")
            self.assertEqual(verification["verification"]["status"], "RECOVERED")
            log("wait incident resolved")
            wait_until(lambda: self._incident_status(incident_id) == "RESOLVED")
        finally:
            log("cleanup fault")
            self._set_fault(INVENTORY_URL, "cpu_saturation", False)


if __name__ == "__main__":
    unittest.main()
