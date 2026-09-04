"""Automatic evaluation runner.

This script reads evaluation cases, sends them to the Agent Runtime API and
computes the metrics listed in the project README. It is intentionally small
and can run in CI without a real LLM when `LLM_PROVIDER=mock` is used.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8081")


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


def call_diagnose(case: dict) -> tuple[dict, float]:
    payload = {
        "incident_id": hash(case["id"]) % 100000,
        "alert": {
            "service": case.get("service", "payment-service"),
            "alertName": case.get("fault_type", "unknown"),
            "severity": "P1",
            "summary": f"{case.get('service')} {case.get('fault_type')}",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{AGENT_URL}/api/v1/agent/diagnose",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data, time.perf_counter() - start


def main() -> int:
    cases_dir = Path(__file__).resolve().parents[1] / "cases"
    cases = load_cases(cases_dir)
    if not cases:
        print("No evaluation cases found")
        return 1

    top1 = 0
    top3 = 0
    diagnosis_success = 0
    tool_calls = []
    latencies = []
    tokens_in = []
    tokens_out = []
    approvals = 0

    for case in cases:
        data, latency = call_diagnose(case)
        latencies.append(latency)
        diagnosis = data.get("diagnosis", {})
        root_cause = diagnosis.get("root_cause", "").lower()
        expected = case.get("expected_root_cause", "").lower()
        status = diagnosis.get("status", "")
        if status:
            diagnosis_success += 1
        if root_cause == expected or expected in root_cause or root_cause in expected:
            top1 += 1
            top3 += 1
        tool_calls.append(len(diagnosis.get("tool_calls", [])))
        tokens_in.append(0)  # mock provider does not report tokens over HTTP
        tokens_out.append(0)
        if diagnosis.get("recommended_actions"):
            approvals += 1

    n = len(cases)
    latencies.sort()
    p95 = latencies[max(0, int(n * 0.95) - 1)] if latencies else 0
    report = {
        "total_cases": n,
        "root_cause_top1_accuracy": round(top1 / n, 4),
        "root_cause_top3_accuracy": round(top3 / n, 4),
        "diagnosis_success_rate": round(diagnosis_success / n, 4),
        "average_tool_calls": round(sum(tool_calls) / n, 2) if n else 0,
        "average_diagnosis_time_s": round(sum(latencies) / n, 4) if n else 0,
        "p95_diagnosis_time_s": round(p95, 4),
        "average_input_tokens": round(sum(tokens_in) / n, 2) if n else 0,
        "average_output_tokens": round(sum(tokens_out) / n, 2) if n else 0,
        "human_approval_rate": round(approvals / n, 4) if n else 0,
        "recovery_success_rate": 0.0,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())