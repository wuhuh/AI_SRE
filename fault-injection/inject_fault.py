"""Fault injection CLI for demo services.

Usage:
    python inject_fault.py redis_pool_exhausted --enable
    python inject_fault.py redis_pool_exhausted --disable
    python inject_fault.py slow_sql --enable
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

SERVICE_ENDPOINTS = {
    "redis_pool_exhausted": "http://localhost:8001/faults?name=redis_pool_exhausted&enabled={enabled}",
    "redis_slow_command": "http://localhost:8001/faults?name=redis_slow_command&enabled={enabled}",
    "thread_pool_exhausted": "http://localhost:8001/faults?name=thread_pool_exhausted&enabled={enabled}",
    "slow_sql": "http://localhost:8003/faults?name=slow_sql&enabled={enabled}",
    "cpu_saturation": "http://localhost:8003/faults?name=cpu_saturation&enabled={enabled}",
    "memory_pressure": "http://localhost:8003/faults?name=memory_pressure&enabled={enabled}",
    "downstream_timeout": "http://localhost:8002/faults?name=downstream_timeout&enabled={enabled}",
}


def call(url: str) -> None:
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fault", choices=list(SERVICE_ENDPOINTS.keys()))
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()

    if args.enable == args.disable:
        print("Must specify exactly one of --enable or --disable")
        return 1
    enabled = "true" if args.enable else "false"
    url = SERVICE_ENDPOINTS[args.fault].format(enabled=enabled)
    call(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())