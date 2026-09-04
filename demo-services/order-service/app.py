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

app = FastAPI(title="order-service")
setup("order-service", metrics_port=int(os.getenv("METRICS_PORT", "8006")))
instrument_fastapi(app, "order-service")

INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory-service:8003")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://payment-service:8001")

order_faults = {
    "downstream_timeout": os.getenv("FAULT_DOWNSTREAM_TIMEOUT", "false") == "true",
}


@app.post("/faults")
def set_fault(name: str, enabled: bool):
    if name not in order_faults:
        return JSONResponse(status_code=404, content={"error": "unknown fault"})
    order_faults[name] = enabled
    logger.info("fault %s set to %s", name, enabled)
    return {"fault": name, "enabled": enabled}


@app.middleware("http")
async def set_request_id(request: Request, call_next):
    token = request_id_var.set(request.headers.get("X-Request-Id", "-"))
    try:
        start = time.perf_counter()
        response = await call_next(request)
        if HTTP_LATENCY:
            HTTP_LATENCY.labels(service="order-service", method=request.method).observe(time.perf_counter() - start)
        if HTTP_REQUESTS:
            HTTP_REQUESTS.labels(service="order-service", method=request.method, status=response.status_code).inc()
        return response
    finally:
        request_id_var.reset(token)


@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}


@app.post("/orders")
def create_order():
    if order_faults["downstream_timeout"]:
        time.sleep(5.0)
        logger.warning("downstream timeout simulated")
    with httpx.Client(timeout=10.0) as client:
        inventory_resp = client.post(f"{INVENTORY_URL}/inventory/check", json={"items": ["sku-1"]})
        if inventory_resp.status_code >= 400:
            logger.error("inventory check failed status=%s", inventory_resp.status_code)
            return JSONResponse(status_code=503, content={"error": "inventory_down"})
        payment_resp = client.post(f"{PAYMENT_URL}/payments", json={"amount": 99.9})
        if payment_resp.status_code >= 400:
            logger.error("payment failed status=%s body=%s", payment_resp.status_code, payment_resp.text)
            return JSONResponse(status_code=503, content={"error": "payment_failed"})
    logger.info("order created")
    return {"orderId": "order-1", "status": "created"}
