"""Local benchmark runner.

Starts the local lightweight API services and runs the Agent benchmark against
them, producing real latency numbers without Docker.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from e2e.local_e2e_runner import (
    AR_PORT,
    CP_PORT,
    INVENTORY_PORT,
    PAYMENT_PORT,
    AgentRuntimeHandler,
    ControlPlaneHandler,
    InventoryHandler,
    PaymentHandler,
    start_server,
)


def main() -> int:
    servers = [
        start_server(CP_PORT, ControlPlaneHandler),
        start_server(AR_PORT, AgentRuntimeHandler),
        start_server(PAYMENT_PORT, PaymentHandler),
        start_server(INVENTORY_PORT, InventoryHandler),
    ]
    env = os.environ.copy()
    env["AGENT_URL"] = f"http://localhost:{AR_PORT}"
    env["RUN_E2E"] = "1"
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "benchmark" / "agent-benchmark.py"),
        "--concurrency",
        "1",
        "--requests",
        "10",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    for server in servers:
        server.shutdown()
        server.server_close()
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
