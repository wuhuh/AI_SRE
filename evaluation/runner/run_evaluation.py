"""Automatic evaluation runner (P0-03 重构版).

结构性修复（对应 docs/project-audit.md P0-03）：
1. 输入不再包含 fault_type —— alert 由中性 symptom 档案构造（build_alert）。
2. 打分改为 canonical 标签精确匹配：Top-1 = 首选根因 == expected 标签；
   Top-3 = expected ∈ candidate_root_causes[:3]（真实 ranked list，不再与 Top-1 同值）。
   双向子串匹配已删除。
3. 支持 splits（dev/validation/test/all），默认 test。
4. 报告落盘 evaluation/results/，并统计 Unknown Rate / Evidence P·R /
   tool 成功率 / 真实 token / P95 时延。

用法：
    python run_evaluation.py --splits test --provider openai --agent-url http://localhost:8081
    python run_evaluation.py --splits all --limit 5   # 冒烟
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8081")

# P0-03: fault_type 只作为 ground truth，绝不进入告警输入。
# P3-EV-01: 每故障 ≥5 条中性表述 + 严重度扰动（按 case id 确定性选取）——
# 单模板会让模型背稿而非判因。
ALERT_PROFILES: dict[str, dict[str, object]] = {
    "redis_connection_pool_exhausted": {
        "alertName": "DependencyErrorsHigh",
        "summaries": [
            "{service} shows intermittent 5xx and timeouts when reaching its caching dependency",
            "{service} connection pool to the cache is exhausted; new cache clients wait indefinitely",
            "{service} reports borrow timeouts on its cache client pool during peak traffic",
            "{service} sees a spike in cache-side connection errors; pooled connections never return",
            "{service} fails cache-backed requests while the cache host itself stays healthy",
        ],
    },
    "redis_slow_command": {
        "alertName": "ServiceLatencyHigh",
        "summaries": [
            "{service} p99 latency is elevated; reads through the caching layer are far above baseline",
            "{service} cache round-trips take orders of magnitude longer than yesterday's baseline",
            "{service} slow-command log on the cache shows frequent multi-second entries",
            "{service} request latency correlates with cache access time, not app CPU",
            "{service} users report slow pages; cache hits are unusually slow while hit-rate is normal",
        ],
    },
    "database_connection_pool_exhausted": {
        "alertName": "ServiceLatencyHigh",
        "summaries": [
            "{service} request latency is climbing; new work stalls while waiting for a database connection",
            "{service} database pool wait time dominates request handling",
            "{service} threads pile up waiting to borrow a DB connection; the pool never frees up",
            "{service} reports connection-acquisition timeouts against its primary datastore",
            "{service} throughput collapses while the database server itself looks idle",
        ],
    },
    "slow_sql": {
        "alertName": "ServiceLatencyHigh",
        "summaries": [
            "{service} p99 latency is elevated; queries that used to take milliseconds now take seconds",
            "{service} slow-query log shows a surge of full scans on its hottest table",
            "{service} API latency spikes align with database statement duration",
            "{service} request handling blocks on a single slow read query per request",
            "{service} degraded response times traced to a long-running query plan",
        ],
    },
    "cpu_saturation": {
        "alertName": "ServiceLatencyHigh",
        "summaries": [
            "{service} latency is rising and requests are queuing; the container is pegged at its processing limit",
            "{service} CPU is saturated; threads spend more time runnable than waiting",
            "{service} compute-bound processing delays every request beyond its SLO",
            "{service} throttling observed; CFS quota consumed before the window ends",
            "{service} worker CPUs at 100% while downstream dependencies remain fast",
        ],
    },
    "memory_leak": {
        "alertName": "ResourcePressureHigh",
        "summaries": [
            "{service} memory usage keeps climbing since the last deploy with growing GC pressure",
            "{service} RSS grows linearly with traffic and never returns to baseline",
            "{service} heap retention increases hour over hour; OOM risk within days",
            "{service} GC pauses lengthen as live set expands after each release",
            "{service} container memory approach its limit; eviction pressure visible",
        ],
    },
    "thread_pool_exhausted": {
        "alertName": "DependencyErrorsHigh",
        "summaries": [
            "{service} requests time out under high concurrency; every worker is busy and new requests queue",
            "{service} worker pool saturated; accept backlog grows while CPU stays low",
            "{service} response times plateau at the queue wait, not at processing time",
            "{service} busy threads stuck on slow downstream calls starve the pool",
            "{service} concurrent request ceiling reached; extra load turns into timeouts",
        ],
    },
    "pod_crashloopbackoff": {
        "alertName": "AvailabilityDegraded",
        "summaries": [
            "{service} instance keeps restarting shortly after becoming ready; intermittent 5xx between restarts",
            "{service} pod restart count climbing; readiness flips between ready and not-ready",
            "{service} workload enters CrashLoopBackOff after the latest rollout",
            "{service} replica restarts every few minutes; errors follow the restart cycle",
            "{service} instance availability flaps; liveness probe kills it before stabilizing",
        ],
    },
    "downstream_http_timeout": {
        "alertName": "DependencyErrorsHigh",
        "summaries": [
            "{service} 5xx spike; calls to an upstream service are timing out and the circuit breaker is open",
            "{service} fails fast on dependency timeouts; fallbacks exhausted",
            "{service} errors trace to a slow upstream; connection established but no response in time",
            "{service} request failure rate mirrors the upstream's response deadline",
            "{service} half-open breaker never recovers; upstream keeps timing out",
        ],
    },
    "rocketmq_message_backlog": {
        "alertName": "QueueLagHigh",
        "summaries": [
            "{service} consumer keeps falling behind; queue depth grows steadily and delivery lags",
            "{service} consumer lag grows monotonically despite a healthy broker",
            "{service} messages accumulate faster than the consumer can drain",
            "{service} delivery delay crosses its SLO; offset advances slower than production",
            "{service} backlog alert fires; consumption rate below ingress by a wide margin",
        ],
    },
}


def _case_variant(case_id: str, modulo: int) -> int:
    """确定性变体选择（EV-01）——不用 hash()（PYTHONHASHSEED 敏感）。"""
    import hashlib
    return int(hashlib.sha256(str(case_id).encode("utf-8")).hexdigest(), 16) % modulo


def normalize_label(value: str | None) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def build_alert(case: dict) -> dict:
    fault = case.get("fault_type", "")
    profile = ALERT_PROFILES.get(fault)
    if profile is None:
        raise KeyError(f"no alert profile for fault_type={fault!r}")
    service = case.get("service", "payment-service")
    summaries = profile["summaries"]
    variant = _case_variant(case.get("id", ""), len(summaries))
    # P3-EV-01: 严重度扰动——后 2/5 表述降为 P2（梯度信噪，不只训练 P1）
    severity = "P1" if variant < 3 else "P2"
    return {
        "service": service,
        "alertName": profile["alertName"],
        "severity": severity,
        "summary": summaries[variant].format(service=service),
    }


def score(diagnosis: dict, expected_label: str) -> tuple[bool, bool]:
    """返回 (top1, top3)。全部为 canonical 标签的精确匹配。"""
    candidates = [normalize_label(c) for c in (diagnosis.get("candidate_root_causes") or [])]
    if not candidates:
        candidates = [normalize_label(diagnosis.get("root_cause", ""))]
    expected = normalize_label(expected_label)
    top1 = bool(candidates) and candidates[0] == expected
    top3 = expected in candidates[:3]
    return top1, top3


def _tag_matched(tag: str, evidence: dict) -> bool:
    """P2-FI-10: 语义标签匹配 —— 期望标签（如 redis_slowlog）按关键词拆分，
    在证据的 key+source+content 中逐词核对。旧实现只对 key 字符串精确匹配，
    而产出 key 是 `tool:step` 序号 → recall 恒 0，指标失真。"""
    text = " ".join(
        [
            str(evidence.get("key", "")),
            str(evidence.get("source", "")),
            str(evidence.get("content", "")),
        ]
    ).lower()
    parts = [p for p in tag.lower().replace("-", "_").split("_") if p]
    return bool(parts) and all(p in text for p in parts)


def evidence_scores(diagnosis: dict, case: dict) -> tuple[float | None, float | None]:
    """Evidence Precision / Recall：期望语义标签 vs 产出证据（key/source/content）。"""
    expected = [k for k in (case.get("expected_evidence") or []) if normalize_label(k)]
    produced = [e for e in (diagnosis.get("evidence") or []) if e]
    if not expected:
        return None, None
    if not produced:
        return 0.0, 0.0
    matched_tags = sum(1 for tag in expected if any(_tag_matched(tag, e) for e in produced))
    recall = matched_tags / len(expected)
    matched_evidence = sum(1 for e in produced if any(_tag_matched(tag, e) for tag in expected))
    precision = matched_evidence / len(produced)
    return round(precision, 4), round(recall, 4)


def load_cases(cases_dir: Path) -> list[dict]:
    cases = []
    for path in sorted(cases_dir.glob("*.yaml")):
        if yaml is not None:
            with open(path, encoding="utf-8") as f:
                cases.append(yaml.safe_load(f))
        else:
            # Minimal fallback parser: only used when PyYAML is unavailable.
            data = {}
            ev = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if ":" in line and not line.startswith("  "):
                    key, val = line.split(":", 1)
                    data[key.strip()] = val.strip()
                elif line.strip().startswith("- "):
                    ev.append(line.strip()[2:])
            data["expected_evidence"] = ev
            cases.append(data)
    return cases


def load_split_ids(splits_dir: Path, split: str) -> set[str] | None:
    path = splits_dir / f"{split}.json"
    if not path.exists():
        return None
    return set(json.loads(path.read_text(encoding="utf-8")))


def call_diagnose(case: dict, agent_url: str = AGENT_URL) -> tuple[dict, float]:
    payload = {
        # P3-EV-02: hash() 受 PYTHONHASHSEED 影响（同 case 重跑 id 漂移）→ sha256 确定性
        "incident_id": _case_variant(case["id"], 100000),
        "alert": build_alert(case),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{agent_url}/api/v1/agent/diagnose",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=240) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data, time.perf_counter() - start


def evaluate(cases: list[dict], agent_url: str = AGENT_URL) -> list[dict]:
    rows = []
    for case in cases:
        try:
            data, latency = call_diagnose(case, agent_url)
        except Exception as e:  # noqa: BLE001 - 单个 case 失败不炸全局，记为 error row
            rows.append(
                {
                    "case_id": case.get("id"),
                    "expected": case.get("fault_type"),
                    "predicted": "http_error",
                    "error": f"{type(e).__name__}: {e}",
                    "candidates": [],
                    "confidence": None,
                    "status": "HTTP_ERROR",
                    "fallback_used": False,
                    "top1": False,
                    "top3": False,
                    "evidence_precision": None,
                    "evidence_recall": None,
                    "tool_calls": 0,
                    "tool_success": 0,
                    "llm_input_tokens": 0,
                    "llm_output_tokens": 0,
                    "latency_s": 0.0,
                }
            )
            continue
        diagnosis = data.get("diagnosis", {})
        top1, top3 = score(diagnosis, case.get("fault_type", ""))
        precision, recall = evidence_scores(diagnosis, case)
        tool_calls = diagnosis.get("tool_calls", []) or []
        rows.append(
            {
                "case_id": case.get("id"),
                "expected": case.get("fault_type"),
                "predicted": diagnosis.get("root_cause", ""),
                "candidates": diagnosis.get("candidate_root_causes", []),
                "confidence": diagnosis.get("confidence"),
                "status": diagnosis.get("status", ""),
                "fallback_used": diagnosis.get("fallback_used", False),
                "top1": top1,
                "top3": top3,
                "evidence_precision": precision,
                "evidence_recall": recall,
                "tool_calls": len(tool_calls),
                "tool_success": sum(1 for t in tool_calls if t.get("status") == "SUCCESS"),
                "llm_input_tokens": diagnosis.get("llm_input_tokens", 0),
                "llm_output_tokens": diagnosis.get("llm_output_tokens", 0),
                "latency_s": round(latency, 3),
            }
        )
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"total_cases": 0}
    scored = [r for r in rows if r["status"] != "HTTP_ERROR"]
    latencies = sorted(r["latency_s"] for r in scored)
    p95 = latencies[max(0, int(len(scored) * 0.95) - 1)] if scored else 0.0
    total_tools = sum(r["tool_calls"] for r in scored)
    successful_tools = sum(r["tool_success"] for r in scored)
    unknown = sum(1 for r in rows if normalize_label(r["predicted"]) == "unknown" or r["status"] == "UNKNOWN")
    fallback = sum(1 for r in rows if r["fallback_used"])
    http_errors = sum(1 for r in rows if r["status"] == "HTTP_ERROR")
    recalls = [r["evidence_recall"] for r in rows if r["evidence_recall"] is not None]
    precisions = [r["evidence_precision"] for r in rows if r["evidence_precision"] is not None]
    return {
        "total_cases": n,
        "http_errors": http_errors,
        "root_cause_top1_accuracy": round(sum(1 for r in scored if r["top1"]) / n, 4) if scored else 0.0,
        "root_cause_top3_accuracy": round(sum(1 for r in scored if r["top3"]) / n, 4) if scored else 0.0,
        "unknown_rate": round(unknown / n, 4),
        "fallback_rate": round(fallback / n, 4),
        "evidence_precision_avg": round(sum(precisions) / len(precisions), 4) if precisions else None,
        "evidence_recall_avg": round(sum(recalls) / len(recalls), 4) if recalls else None,
        "tool_success_rate": round(successful_tools / total_tools, 4) if total_tools else None,
        "average_tool_calls": round(total_tools / len(scored), 2) if scored else 0,
        "average_diagnosis_time_s": round(sum(latencies) / len(scored), 3) if scored else 0,
        "p95_diagnosis_time_s": round(p95, 3),
        "average_input_tokens": round(sum(r["llm_input_tokens"] for r in scored) / len(scored), 1) if scored else 0,
        "average_output_tokens": round(sum(r["llm_output_tokens"] for r in scored) / len(scored), 1) if scored else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", default="test", choices=["dev", "validation", "test", "all"])
    parser.add_argument(
        "--provider", default=os.getenv("LLM_PROVIDER", "mock"), help="报告元数据：本次评测使用的 LLM provider"
    )
    parser.add_argument("--agent-url", default=AGENT_URL)
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 个 case（冒烟用）")
    parser.add_argument("--types", default="", help="逗号分隔 fault_type 过滤（P0-08：只跑已注入真实故障的类型）")
    parser.add_argument("--services", default="", help="逗号分隔 service 过滤（P0-08：只跑部署栈里真实存在故障的服务）")
    parser.add_argument("--tag", default="", help="结果文件名附加标记（如 real-fault）")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    cases = load_cases(base / "cases")
    if not cases:
        print("No evaluation cases found")
        return 1
    if args.splits != "all":
        ids = load_split_ids(base / "splits", args.splits)
        if ids is None:
            print(f"Split file not found: {args.splits}")
            return 1
        cases = [c for c in cases if c.get("id") in ids]
    if args.types:
        wanted = {t.strip() for t in args.types.split(",") if t.strip()}
        cases = [c for c in cases if c.get("fault_type") in wanted]
    if args.services:
        wanted_svcs = {s.strip() for s in args.services.split(",") if s.strip()}
        cases = [c for c in cases if c.get("service") in wanted_svcs]
    if args.limit > 0:
        cases = cases[: args.limit]

    rows = evaluate(cases, args.agent_url)
    report = summarize(rows)
    report["provider"] = args.provider
    report["split"] = args.splits
    report["input_mode"] = "neutral_symptom_alerts (no fault_type leakage)"
    report["scoring"] = "exact canonical label match; top3 = expected in candidates[:3]"
    if args.tag:
        report["tag"] = args.tag

    results_dir = base / "results"
    results_dir.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_{args.tag}" if args.tag else ""
    out = results_dir / f"eval_{stamp}_{args.splits}_{args.provider}{suffix}.json"
    out.write_text(json.dumps({"report": report, "cases": rows}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"results written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
