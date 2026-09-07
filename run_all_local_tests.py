"""Run all local tests and validations without Docker."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd, cwd=ROOT):
    print(f"\n$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=str(cwd))


def main() -> int:
    checks = [
        ([sys.executable, "-m", "unittest", "discover", "-s", "tests"], ROOT / "agent-runtime"),
        ([sys.executable, "e2e/local_contract_smoke.py"], ROOT),
        ([sys.executable, "evaluation/runner/run_baseline.py"], ROOT),
    ]
    for cmd, cwd in checks:
        result = run(cmd, cwd)
        if result.returncode != 0:
            return result.returncode
    print("\nAll local tests passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())