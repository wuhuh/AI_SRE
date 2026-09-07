"""Concurrent incident benchmark against Agent Runtime (P2-BM-02).

- 真实链路：直连 agent-runtime /api/v1/agent/diagnose（非 mock server）。
- 错误处理：逐请求记录 HTTP 状态，失败计入 error_rate 而非崩溃。
- 阈值门禁：--max-p95-s / --max-error-rate 超限 exit 1（可接 CI）。
- 结果落盘：--output 写 JSON（含 provider/target 分层标注），无 -o 时仅打印。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request


def diagnose(url: str, i: int) -> tuple[float, int]:
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
        f"{url.rstrip('/')}/api/v1/agent/diagnose",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
        return time.perf_counter() - start, resp.status
    except urllib.error.HTTPError as e:
        return time.perf_counter() - start, e.code
    except Exception:
        return time.perf_counter() - start, 500


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("AGENT_URL", "http://localhost:8081"))
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--max-p95-s", type=float, default=30.0,
                        help="p95 时延阈值（秒），超限 exit 1")
    parser.add_argument("--max-error-rate", type=float, default=0.0,
                        help="错误率阈值，超限 exit 1")
    parser.add_argument("--output", help="结果 JSON 落盘路径")
    parser.add_argument("--provider", default=os.getenv("LLM_PROVIDER", "mock"),
                        help="LLM 供应商标注（mock / openai-compatible）")
    args = parser.parse_args()

    wall_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(diagnose, args.url, i) for i in range(args.requests)]
        results = [f.result() for f in futures]
    wall_s = time.perf_counter() - wall_start

    latencies = sorted(r[0] for r in results)
    errors = sum(1 for _, code in results if code >= 400)
    n = len(latencies)
    error_rate = errors / n if n else 0.0
    p95 = latencies[max(0, int(n * 0.95) - 1)] if n else 0.0

    report = {
        "target": "agent-runtime:/api/v1/agent/diagnose（真实诊断链路）",
        "provider": args.provider,
        "requests": n,
        "concurrency": args.concurrency,
        "errors": errors,
        "error_rate": round(error_rate, 4),
        "avg_s": round(sum(latencies) / n, 3) if n else 0,
        "p95_s": round(p95, 3),
        "wall_s": round(wall_s, 3),
        "throughput_rps": round(n / wall_s, 2) if wall_s else 0,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    failed = p95 > args.max_p95_s or error_rate > args.max_error_rate
    if failed:
        print(f"THRESHOLD BREACH: p95={p95:.2f}s (max {args.max_p95_s}) "
              f"error_rate={error_rate:.4f} (max {args.max_error_rate})", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
