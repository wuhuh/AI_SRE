from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.observability import HTTP_LATENCY, HTTP_REQUESTS, instrument_fastapi, request_id_var, setup

logger = logging.getLogger(__name__)

app = FastAPI(title="inventory-service")
setup("inventory-service", metrics_port=int(os.getenv("METRICS_PORT", "8007")))
instrument_fastapi(app, "inventory-service")

inventory_faults = {
    "slow_sql": os.getenv("FAULT_SLOW_SQL", "false") == "true",
    "cpu_saturation": os.getenv("FAULT_CPU_SATURATION", "false") == "true",
    "memory_pressure": os.getenv("FAULT_MEMORY_PRESSURE", "false") == "true",
}


@app.post("/faults")
def set_fault(name: str, enabled: bool):
    if name not in inventory_faults:
        return JSONResponse(status_code=404, content={"error": "unknown fault"})
    inventory_faults[name] = enabled
    logger.info("fault %s set to %s", name, enabled)
    return {"fault": name, "enabled": enabled}


@app.middleware("http")
async def set_request_id(request: Request, call_next):
    token = request_id_var.set(request.headers.get("X-Request-Id", "-"))
    try:
        start = time.perf_counter()
        response = await call_next(request)
        if HTTP_LATENCY:
            HTTP_LATENCY.labels(service="inventory-service", method=request.method).observe(time.perf_counter() - start)
        if HTTP_REQUESTS:
            HTTP_REQUESTS.labels(service="inventory-service", method=request.method, status=response.status_code).inc()
        return response
    finally:
        request_id_var.reset(token)


@app.get("/health")
def health():
    return {"status": "ok", "service": "inventory-service"}


@app.post("/inventory/check")
def check_inventory():
    if inventory_faults["memory_pressure"]:
        _ = [bytearray(1024 * 1024) for _ in range(30)]
        logger.warning("memory pressure simulated")
    if inventory_faults["slow_sql"]:
        time.sleep(2.0)
        logger.warning("degraded inventory query detected")
    if inventory_faults["cpu_saturation"]:
        # P0-08: 真实 CPU 饱和——uvicorn 进程内持续计算，process_cpu 指标随之升高
        # （原纯 sleep 只抬高时延，Prometheus 的 process_cpu 看不见）
        import hashlib
        burn_until = time.perf_counter() + float(os.getenv("CPU_BURN_SECONDS", "0.6"))
        payload = b"inventory-check"
        while time.perf_counter() < burn_until:
            payload = hashlib.sha256(payload).digest()
    return {"items": ["sku-1"], "available": True}

