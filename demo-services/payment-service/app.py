from __future__ import annotations

import logging
import os
import threading
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
    # P0-08 二期：真实有界连接池（默认 2）——故障 = 真实占满，请求侧真实 ConnectionError
    REDIS_POOL = redis.ConnectionPool.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        max_connections=int(os.getenv("REDIS_POOL_MAX", "2")),
    )
    REDIS_CLIENT = redis.Redis(connection_pool=REDIS_POOL)
except Exception:  # pragma: no cover
    REDIS_POOL = None
    REDIS_CLIENT = None

payment_faults = {
    "redis_pool_exhausted": os.getenv("FAULT_REDIS_POOL_EXHAUSTED", "false") == "true",
    "redis_slow_command": os.getenv("FAULT_REDIS_SLOW_COMMAND", "false") == "true",
    "thread_pool_exhausted": os.getenv("FAULT_THREAD_POOL_EXHAUSTED", "false") == "true",
}

_DRAIN_THREADS: list = []


def _hold_pool_connection() -> None:
    """占住一条真实 redis 连接：BLPOP(1s) 循环直到故障关闭，再归还。"""
    conn = REDIS_POOL.get_connection("BLPOP")
    try:
        while payment_faults["redis_pool_exhausted"]:
            try:
                conn.send_command("BLPOP", "payment:pool_drain", 1)
                conn.read_response()
            except redis.exceptions.ConnectionError:
                time.sleep(0.5)
    finally:
        REDIS_POOL.release(conn)


def _set_pool_drain(enabled: bool) -> None:
    threads = [t for t in _DRAIN_THREADS if t.is_alive()]
    if enabled and len(threads) < REDIS_POOL.max_connections:
        for _ in range(REDIS_POOL.max_connections - len(threads)):
            t = threading.Thread(target=_hold_pool_connection, daemon=True)
            t.start()
            _DRAIN_THREADS.append(t)


@app.post("/faults")
def set_fault(name: str, enabled: bool):
    if name not in payment_faults:
        return JSONResponse(status_code=404, content={"error": "unknown fault"})
    payment_faults[name] = enabled
    if name == "redis_pool_exhausted" and REDIS_POOL is not None:
        # P0-08 二期：真实打满——后台线程持占全部池连接，请求侧收真实 ConnectionError
        threading.Thread(target=_set_pool_drain, args=(enabled,), daemon=True).start()
        logger.info("redis pool drain %s (real pool max_connections=%s)",
                    "enabled" if enabled else "disabled", REDIS_POOL.max_connections)
    else:
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
    if payment_faults["thread_pool_exhausted"]:
        logger.error("ThreadPoolExhaustedException: pool exhausted (fault injected)")
        return JSONResponse(status_code=503, content={"error": "thread_pool_exhausted"})
    if payment_faults["redis_slow_command"]:
        time.sleep(1.5)
        logger.warning("redis slow command simulated latency")
    if REDIS_CLIENT is not None:
        try:
            REDIS_CLIENT.incr("payment:count")
        except redis.exceptions.ConnectionError as exc:
            # P0-08 二期：真实异常入日志（含 "Too many connections"），不再伪造结论词
            logger.error("redis pool acquisition failed: %s", exc)
            return JSONResponse(status_code=503, content={"error": "redis_pool_exhausted"})
    logger.info("payment created amount=%s", amount)
    return {"paymentId": "pay-1", "status": "success", "amount": amount}