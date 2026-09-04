"""Split evaluation cases into dev/validation/held-out test sets."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"
OUT_DIR = Path(__file__).resolve().parents[1] / "splits"


def main():
    random.seed(42)
    ids = sorted(p.stem for p in CASES_DIR.glob("*.yaml"))
    random.shuffle(ids)
    n = len(ids)
    dev = ids[: int(n * 0.8)]
    val = ids[int(n * 0.8): int(n * 0.9)]
    test = ids[int(n * 0.9):]
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "dev.json").write_text(json.dumps(dev, indent=2), encoding="utf-8")
    (OUT_DIR / "validation.json").write_text(json.dumps(val, indent=2), encoding="utf-8")
    (OUT_DIR / "test.json").write_text(json.dumps(test, indent=2), encoding="utf-8")
    print(json.dumps({"dev": len(dev), "validation": len(val), "test": len(test)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())