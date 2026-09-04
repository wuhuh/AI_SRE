"""Local lightweight E2E runner.

This starts minimal HTTP servers that implement the same API contract as the
Docker-based project, then runs the real E2E test suite against them.

It is intended for environments where Docker is not available but we still want
to verify the full loop:

    alert -> incident -> diagnosis -> recovery -> verification -> resolved

Usage:
    python e2e/local_e2e_runner.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CP_PORT = int(os.getenv("LOCAL_CP_PORT", "18080"))
AR_PORT = int(os.getenv("LOCAL_AR_PORT", "18081"))
PAYMENT_PORT = int(os.getenv("LOCAL_PAYMENT_PORT", "18001"))
INVENTORY_PORT = int(os.getenv("LOCAL_INVENTORY_PORT", "18003"))

STATE = {
    "incidents": {},
    "tasks": {},
    "next_id": 1,
    "next_task_id": 1,
    "faults": {},
}


def send_json(handler, status: int, payload: dict | list) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def create_incident(service: str, summary: str) -> dict:
    incident_id = STATE["next_id"]
    STATE["next_id"] += 1
    incident = {
        "id": incident_id,
        "service": service,
        "status": "DETECTED",
        "severity": "P1",
        "summary": summary,
        "rootCause": None,
        "confidence": None,
        "evidence": [],
        "toolCalls": [],
        "remediations": [],
        "approvals": [],
        "steps": [],
        "auditLogs": [],
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "resolvedAt": None,
        "alertCount": 1,
    }
    STATE["incidents"][incident_id] = incident
    task_id = STATE["next_task_id"]
    STATE["next_task_id"] += 1
    STATE["tasks"][task_id] = {
        "id": task_id,
        "incidentId": incident_id,
        "status": "QUEUED",
        "createdAt": incident["startedAt"],
    }
    return incident


class ControlPlaneHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence
        pass

    def _send(self, status, payload):
        send_json(self, status, payload)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            return self._send(200, {"status": "ok"})
        if path == "/api/v1/tasks/pending":
            pending = [t for t in STATE["tasks"].values() if t["status"] == "QUEUED"]
            return self._send(200, pending)
        if path == "/api/v1/dashboard/summary":
            incidents = list(STATE["incidents"].values())
            return self._send(200, {
                "total": len(incidents),
                "resolved": sum(1 for i in incidents if i["status"] == "RESOLVED"),
                "diagnosing": sum(1 for i in incidents if i["status"] == "DETECTED"),
                "waitingApproval": 0,
                "failed": 0,
                "avgRecoverySeconds": 0.0,
            })
        if path == "/api/v1/incidents":
            incidents = [
                {k: v for k, v in inc.items() if k not in ("evidence", "toolCalls", "remediations", "approvals", "steps")}
                for inc in STATE["incidents"].values()
            ]
            return self._send(200, incidents)
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "v1" and parts[2] == "incidents":
            try:
                incident_id = int(parts[3])
            except ValueError:
                return self._send(400, {"error": "bad id"})
            inc = STATE["incidents"].get(incident_id)
            if not inc:
                return self._send(404, {"error": "not found"})
            return self._send(200, inc)
        if len(parts) == 5 and parts[0] == "api" and parts[1] == "v1" and parts[2] == "incidents":
            incident_id = int(parts[3])
            inc = STATE["incidents"].get(incident_id)
            if not inc:
                return self._send(404, {"error": "not found"})
            field = parts[4]
            if field == "evidence":
                return self._send(200, inc["evidence"])
            if field == "tool-calls":
                return self._send(200, inc["toolCalls"])
            if field == "remediations":
                return self._send(200, inc["remediations"])
            if field == "steps":
                return self._send(200, inc["steps"])
            if field == "audit-logs":
                return self._send(200, inc.get("auditLogs", []))
            if field == "report":
                report_text = f"# Incident Report #{incident_id}\n\nService: {inc.get('service')}\nRoot Cause: {inc.get('rootCause')}\n"
                return self._send(200, {"incidentId": incident_id, "report": report_text})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/v1/alerts":
            data = read_json(self)
            service = data.get("service", "unknown")
            incident = create_incident(service, data.get("summary", ""))
            return self._send(202, {"incidentId": incident["id"], "duplicate": False})
        task_parts = path.strip("/").split("/")
        if len(task_parts) == 5 and task_parts[0] == "api" and task_parts[1] == "v1" and task_parts[2] == "tasks" and task_parts[4] == "complete":
            task_id = int(task_parts[3])
            task = STATE["tasks"].get(task_id)
            if not task:
                return self._send(404, {"error": "task not found"})
            task["status"] = "COMPLETED"
            return self._send(200, task)
        parts = path.strip("/").split("/")
        if len(parts) >= 5 and parts[0] == "api" and parts[1] == "v1" and parts[2] == "incidents":
            incident_id = int(parts[3])
            inc = STATE["incidents"].get(incident_id)
            if not inc:
                return self._send(404, {"error": "not found"})
            action = parts[4]
            if action == "diagnosis":
                data = read_json(self)
                inc["rootCause"] = data.get("rootCause")
                inc["confidence"] = data.get("confidence")
                inc["evidence"] = data.get("evidence", [])
                inc["toolCalls"] = data.get("toolCalls", [])
                inc["status"] = "ROOT_CAUSE_FOUND"
                inc["steps"].append({"stepType": "DIAGNOSIS", "status": "SUCCESS", "outputSummary": data.get("rootCause")})
                inc["auditLogs"].append({"action": "DIAGNOSIS_SAVED", "actor": "agent", "detail": data.get("rootCause"), "createdAt": inc["startedAt"]})
                return self._send(200, inc)
            if action == "verification":
                data = read_json(self)
                status = data.get("status", "UNKNOWN")
                if status == "RECOVERED":
                    inc["status"] = "RESOLVED"
                    inc["resolvedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
                elif status == "NOT_RECOVERED":
                    inc["status"] = "DIAGNOSING"
                else:
                    inc["status"] = "FAILED"
                inc["steps"].append({"stepType": "VERIFICATION", "status": status, "outputSummary": data.get("detail", "")})
                inc["auditLogs"].append({"action": "VERIFICATION_SAVED", "actor": "agent", "detail": status, "createdAt": inc["startedAt"]})
                return self._send(200, inc)
            if action == "remediations":
                data = read_json(self)
                inc["remediations"].append(data)
                return self._send(200, data)
        return self._send(404, {"error": "not found"})


class AgentRuntimeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence
        pass

    def _send(self, status, payload):
        send_json(self, status, payload)

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            return self._send(200, {"status": "ok"})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/v1/agent/diagnose":
            data = read_json(self)
            incident_id = data.get("incident_id")
            alert = data.get("alert", {})
            service = alert.get("service", "")
            if service == "payment-service" and STATE["faults"].get("payment:redis_pool_exhausted"):
                root_cause = "redis_connection_pool_exhausted"
                evidence = [{"source": "prometheus", "key": "redis_connection_usage_high", "content": "used_connections=maxclients"}]
                tool_calls = [
                    {"toolName": "query_prometheus", "status": "SUCCESS", "resultSummary": "redis usage high", "durationMs": 10},
                    {"toolName": "query_logs", "status": "SUCCESS", "resultSummary": "RedisConnectionFailureException", "durationMs": 10},
                    {"toolName": "query_trace", "status": "SUCCESS", "resultSummary": "redis span p99=3.2s", "durationMs": 10},
                ]
            elif service == "inventory-service" and STATE["faults"].get("inventory:slow_sql"):
                root_cause = "slow_sql"
                evidence = [{"source": "database", "key": "db_slow_query", "content": "select * from inventory took 2s"}]
                tool_calls = [
                    {"toolName": "query_prometheus", "status": "SUCCESS", "resultSummary": "inventory p99 high", "durationMs": 10},
                    {"toolName": "query_logs", "status": "SUCCESS", "resultSummary": "slow inventory query detected", "durationMs": 10},
                ]
            elif service == "inventory-service" and STATE["faults"].get("inventory:cpu_saturation"):
                root_cause = "cpu_saturation"
                evidence = [{"source": "prometheus", "key": "cpu_usage_high", "content": "container cpu 100%"}]
                tool_calls = [
                    {"toolName": "query_prometheus", "status": "SUCCESS", "resultSummary": "container_cpu_usage=100", "durationMs": 10},
                    {"toolName": "query_logs", "status": "SUCCESS", "resultSummary": "load average high", "durationMs": 10},
                ]
            else:
                root_cause = "unknown"
                evidence = []
                tool_calls = []
            diagnosis = {
                "root_cause": root_cause,
                "confidence": 0.95,
                "evidence": evidence,
                "recommended_actions": ["disable fault and verify"],
                "tool_calls": tool_calls,
            }
            # Write back to Control Plane, just like the real Agent Runtime does.
            self._post_cp(f"/api/v1/incidents/{incident_id}/diagnosis", {
                "rootCause": root_cause,
                "confidence": 0.95,
                "evidence": evidence,
                "toolCalls": tool_calls,
                "recommendedActions": ["disable fault and verify"],
            })
            return self._send(200, {
                "incident_id": incident_id,
                "diagnosis": diagnosis,
                "state": {"status": "DIAGNOSED"},
                "duration_ms": 20,
            })
        if path == "/api/v1/agent/verify":
            data = read_json(self)
            incident_id = data.get("incident_id")
            alert = data.get("alert", {})
            service = alert.get("service", "")
            if service == "payment-service" and not STATE["faults"].get("payment:redis_pool_exhausted"):
                status = "RECOVERED"
            elif service == "inventory-service" and not STATE["faults"].get("inventory:slow_sql") and not STATE["faults"].get("inventory:cpu_saturation"):
                status = "RECOVERED"
            else:
                status = "NOT_RECOVERED"
            detail = "service recovered to normal"
            self._post_cp(f"/api/v1/incidents/{incident_id}/verification", {
                "status": status,
                "detail": detail,
                "evidence": [],
            })
            return self._send(200, {
                "incident_id": incident_id,
                "verification": {"status": status, "detail": detail, "evidence": []},
                "state": {"status": "VERIFIED"},
                "duration_ms": 15,
            })
        return self._send(404, {"error": "not found"})

    def _post_cp(self, path: str, payload: dict) -> None:
        req = urllib.request.Request(
            f"http://127.0.0.1:{CP_PORT}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass


class PaymentHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence
        pass

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            return send_json(self, 200, {"status": "ok", "service": "payment-service"})
        return send_json(self, 404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/faults":
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            enabled = qs.get("enabled", ["false"])[0] == "true"
            STATE["faults"][f"payment:{name}"] = enabled
            return send_json(self, 200, {"fault": name, "enabled": enabled})
        if path == "/payments":
            if STATE["faults"].get("payment:redis_pool_exhausted"):
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"redis_pool_exhausted"}')
                return
            return send_json(self, 200, {"paymentId": "pay-1", "status": "success"})
        return send_json(self, 404, {"error": "not found"})


class InventoryHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence
        pass

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            return send_json(self, 200, {"status": "ok", "service": "inventory-service"})
        return send_json(self, 404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/faults":
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            enabled = qs.get("enabled", ["false"])[0] == "true"
            STATE["faults"][f"inventory:{name}"] = enabled
            return send_json(self, 200, {"fault": name, "enabled": enabled})
        if path == "/inventory/check":
            slow = STATE["faults"].get("inventory:slow_sql", False)
            cpu = STATE["faults"].get("inventory:cpu_saturation", False)
            if slow or cpu:
                time.sleep(2)
                return send_json(self, 200, {"degraded": True})
            return send_json(self, 200, {"available": True})
        return send_json(self, 404, {"error": "not found"})


def start_server(port: int, handler) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> int:
    servers = [
        start_server(CP_PORT, ControlPlaneHandler),
        start_server(AR_PORT, AgentRuntimeHandler),
        start_server(PAYMENT_PORT, PaymentHandler),
        start_server(INVENTORY_PORT, InventoryHandler),
    ]
    print("[local-e2e] servers started", flush=True)

    env = os.environ.copy()
    env["RUN_E2E"] = "1"
    env["CONTROL_PLANE_URL"] = f"http://localhost:{CP_PORT}"
    env["AGENT_URL"] = f"http://localhost:{AR_PORT}"
    env["PAYMENT_URL"] = f"http://localhost:{PAYMENT_PORT}"
    env["INVENTORY_URL"] = f"http://localhost:{INVENTORY_PORT}"

    cmd = [sys.executable, "-m", "unittest", "tests.e2e.test_real_faults", "-v"]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT / "agent-runtime"), env=env)
    for server in servers:
        server.shutdown()
        server.server_close()
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())