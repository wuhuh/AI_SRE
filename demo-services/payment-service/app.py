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

app = FastAPI(title="payment-service")
setup("payment-service", metrics_port=int(os.getenv("METRICS_PORT", "8004")))
instrument_fastapi(app, "payment-service")

try:
    import redis
    REDIS_CLIENT = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
except Exception:  # pragma: no cover
    REDIS_CLIENT = None

payment_faults = {
    "redis_pool_exhausted": os.getenv("FAULT_REDIS_POOL_EXHAUSTED", "false") == "true",
    "redis_slow_command": os.getenv("FAULT_REDIS_SLOW_COMMAND", "false") == "true",
    "thread_pool_exhausted": os.getenv("FAULT_THREAD_POOL_EXHAUSTED", "false") == "true",
}


@app.post("/faults")
def set_fault(name: str, enabled: bool):
    if name not in payment_faults:
        return JSONResponse(status_code=404, content={"error": "unknown fault"})
    payment_faults[name] = enabled
    logger.info("fault %s set to %s", name, enabled)
    return {"fault": name, "enabled": enabled}


@app.middleware("http")
async def set_request_id(request: Request, call_next):
    token = request_id_var.set(request.headers.get("X-Request-Id", "-"))
    try:
        start = time.perf_counter()
        response = await call_next(request)
        if HTTP_LATENCY:
            HTTP_LATENCY.labels(service="payment-service", method=request.method).observe(time.perf_counter() - start)
        if HTTP_REQUESTS:
            HTTP_REQUESTS.labels(service="payment-service", method=request.method, status=response.status_code).inc()
        return response
    finally:
        request_id_var.reset(token)


@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-service"}


@app.post("/payments")
def create_payment(amount: float = 10.0):
    if payment_faults["redis_pool_exhausted"]:
        logger.error("RedisConnectionFailureException: pool exhausted (fault injected)")
        return JSONResponse(status_code=503, content={"error": "redis_pool_exhausted"})
    if payment_faults["thread_pool_exhausted"]:
        logger.error("ThreadPoolExhaustedException: pool exhausted (fault injected)")
        return JSONResponse(status_code=503, content={"error": "thread_pool_exhausted"})
    if payment_faults["redis_slow_command"]:
        time.sleep(1.5)
        logger.warning("redis slow command simulated latency")
    if REDIS_CLIENT is not None:
        REDIS_CLIENT.incr("payment:count")
    logger.info("payment created amount=%s", amount)
    return {"paymentId": "pay-1", "status": "success", "amount": amount}