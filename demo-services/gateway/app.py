from __future__ import annotations

import logging
import os
import time
import uuid

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
    # P3-FI-11: 入站无 X-Request-Id 时生成（原恒 "-"），并回写响应头供下游追踪
    req_id = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"
    token = request_id_var.set(req_id)
    try:
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = req_id
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
    # P3-FI-11: 请求 ID 透传到 order-service（链路可从 gateway 一路对上）
    with httpx.Client(timeout=5.0, headers={"X-Request-Id": request_id_var.get()}) as client:
        resp = client.post(f"{ORDER_URL}/orders", json={})
        if resp.status_code >= 400:
            logger.error("order upstream failed status=%s body=%s", resp.status_code, resp.text)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    return resp.json()
