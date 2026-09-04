"""Local API load test runner.

Starts local lightweight services and runs a small concurrent load test against
Alert ingestion and Incident query APIs, producing real QPS / P95 / P99 numbers
without Docker.
"""
from __future__ import annotations

import concurrent.futures
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from e2e.local_e2e_runner import (
    CP_PORT,
    AgentRuntimeHandler,
    ControlPlaneHandler,
    InventoryHandler,
    PaymentHandler,
    start_server,
)


def request(method: str, url: str, payload: dict | None = None, timeout: float = 5.0):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
        return time.perf_counter() - start, 200
    except urllib.error.HTTPError as e:
        return time.perf_counter() - start, e.code
    except Exception:
        return time.perf_counter() - start, 500


def run_load(url: str, method: str, payload: dict | None, requests: int, concurrency: int) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(request, method, url, payload) for _ in range(requests)]
        results = [f.result() for f in futures]
    latencies = sorted(r[0] for r in results)
    errors = [r for r in results if r[1] >= 400]
    total = sum(r[0] for r in results)
    n = len(latencies)
    return {
        "requests": n,
        "concurrency": concurrency,
        "qps": round(n / total, 1) if total else 0,
        "p50_ms": round(latencies[max(0, int(n * 0.50) - 1)] * 1000, 1),
        "p95_ms": round(latencies[max(0, int(n * 0.95) - 1)] * 1000, 1),
        "p99_ms": round(latencies[max(0, int(n * 0.99) - 1)] * 1000, 1),
        "error_rate": round(len(errors) / n, 4),
    }


def main() -> int:
    servers = [
        start_server(CP_PORT, ControlPlaneHandler),
        start_server(CP_PORT + 1, AgentRuntimeHandler),
        start_server(CP_PORT + 2, PaymentHandler),
        start_server(CP_PORT + 3, InventoryHandler),
    ]
    # Note: ports are unique by using CP_PORT offsets.
    cp_url = f"http://localhost:{CP_PORT}"
    # The above starts CP on CP_PORT and others on +1/+2/+3, so only CP is used here.
    alert_payload = {
        "service": "payment-service",
        "alertName": "load_test",
        "resource": "payment-load",
        "severity": "P1",
        "summary": "load test alert",
    }
    alert_report = run_load(f"{cp_url}/api/v1/alerts", "POST", alert_payload, requests=50, concurrency=10)
    incident_report = run_load(f"{cp_url}/api/v1/incidents", "GET", None, requests=50, concurrency=10)
    report = {
        "alert_ingestion": alert_report,
        "incident_query": incident_report,
    }
    print(json.dumps(report, indent=2))
    for server in servers:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())