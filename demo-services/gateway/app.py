from __future__ import annotations

import logging
import os
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.observability import HTTP_LATENCY, HTTP_REQUESTS, instrument_fastapi, request_id_var, setup

logger = logging.getLogger(__name__)

app = FastAPI(title="api-gateway")
setup("api-gateway", metrics_port=int(os.getenv("METRICS_PORT", "8005")))
instrument_fastapi(app, "api-gateway")

ORDER_URL = os.getenv("ORDER_URL", "http://order-service:8002")


@app.middleware("http")
async def set_request_id(request: Request, call_next):
    token = request_id_var.set(request.headers.get("X-Request-Id", "-"))
    try:
        start = time.perf_counter()
        response = await call_next(request)
        if HTTP_LATENCY:
            HTTP_LATENCY.labels(service="api-gateway", method=request.method).observe(time.perf_counter() - start)
        if HTTP_REQUESTS:
            HTTP_REQUESTS.labels(service="api-gateway", method=request.method, status=response.status_code).inc()
        return response
    finally:
        request_id_var.reset(token)


@app.get("/health")
def health():
    return {"status": "ok", "service": "api-gateway"}


@app.post("/api/orders")
def create_order():
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(f"{ORDER_URL}/orders", json={})
        if resp.status_code >= 400:
            logger.error("order upstream failed status=%s body=%s", resp.status_code, resp.text)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    return resp.json()
