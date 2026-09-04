"""Concurrent incident benchmark against Agent Runtime."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
import urllib.request

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8081")


def diagnose(i: int) -> float:
    payload = {
        "incident_id": i,
        "alert": {
            "service": "payment-service",
            "alertName": f"bench-{i}",
            "severity": "P1",
            "summary": "redis pool exhausted",
        },
    }
    req = urllib.request.Request(
        f"{AGENT_URL}/api/v1/agent/diagnose",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=20)
    args = parser.parse_args()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(diagnose, i) for i in range(args.requests)]
        latencies = [f.result() for f in futures]

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    print(json.dumps({
        "requests": len(latencies),
        "concurrency": args.concurrency,
        "avg_s": round(sum(latencies) / len(latencies), 3),
        "p95_s": round(p95, 3),
    }, indent=2))


if __name__ == "__main__":
    main()