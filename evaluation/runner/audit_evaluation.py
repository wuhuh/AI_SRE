"""Evaluation data quality audit.

Checks:
- duplicate case ids
- duplicate content
- answer leakage: expected root cause equals fault_type
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"


def parse_case(path: Path) -> dict:
    data = {}
    ev = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if ":" in line and not line.startswith("  "):
            key, val = line.split(":", 1)
            data[key.strip()] = val.strip()
        elif line.strip().startswith("- "):
            ev.append(line.strip()[2:])
    data["expected_evidence"] = ev
    return data


def main():
    cases = []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        data = parse_case(path)
        data["_path"] = str(path)
        cases.append(data)

    ids = [c.get("id", "") for c in cases]
    dup_ids = [k for k, v in Counter(ids).items() if v > 1]
    summaries = [c.get("summary", "") for c in cases if c.get("summary", "")]
    dup_summaries = len(summaries) - len(set(summaries))
    leakage = [
        c["_path"]
        for c in cases
        if c.get("expected_root_cause", "").replace("_", " ") == c.get("fault_type", "").replace("_", " ")
    ]

    report = {
        "total_cases": len(cases),
        "duplicate_ids": dup_ids,
        "duplicate_summaries": dup_summaries,
        "root_cause_equals_fault_type_count": len(leakage),
        "leakage_examples": leakage[:10],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not dup_ids and not dup_summaries else 1


if __name__ == "__main__":
    sys.exit(main())