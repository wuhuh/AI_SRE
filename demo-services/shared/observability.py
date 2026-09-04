"""Shared OpenTelemetry and Prometheus setup for demo services.

The code degrades gracefully when OTel/Prometheus clients are not installed,
so the services can still start in a minimal environment.
"""
from __future__ import annotations

import contextvars
import logging
import os
import socket
import sys

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_INSTANCE_ID
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    _OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - depends on environment
    _OTEL_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, start_http_server
    _PROMETHEUS_AVAILABLE = True
except Exception:  # pragma: no cover
    _PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

HTTP_REQUESTS = None
HTTP_LATENCY = None
if _PROMETHEUS_AVAILABLE:
    HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["service", "method", "status"])
    HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP latency", ["service", "method"])


class ContextFilter(logging.Filter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service_name = self.service_name
        record.requestId = request_id_var.get()
        if _OTEL_AVAILABLE:
            span = trace.get_current_span()
            span_context = span.get_span_context() if span else None
            if span_context and span_context.is_valid:
                record.traceId = format(span_context.trace_id, "032x")
                record.spanId = format(span_context.span_id, "016x")
            else:
                record.traceId = "-"
                record.spanId = "-"
        else:
            record.traceId = "-"
            record.spanId = "-"
        return True


request_id_var = contextvars.ContextVar("request_id", default="-")


def setup(service_name: str, otlp_endpoint: str | None = None, metrics_port: int | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s service=%(service_name)s level=%(levelname)s traceId=%(traceId)s spanId=%(spanId)s requestId=%(requestId)s message=%(message)s",
        force=True,
    )
    for handler in logging.root.handlers:
        handler.addFilter(ContextFilter(service_name))
    if _OTEL_AVAILABLE:
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_INSTANCE_ID: socket.gethostname(),
        })
        provider = TracerProvider(resource=resource)
        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint + "/v1/traces")))
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry enabled for %s", service_name)
    else:
        logger.warning("OpenTelemetry packages not installed; traces are disabled for %s", service_name)
    if _PROMETHEUS_AVAILABLE and metrics_port:
        start_http_server(metrics_port)
        logger.info("Prometheus metrics listening on %s", metrics_port)


def instrument_fastapi(app, service_name: str) -> None:
    if _OTEL_AVAILABLE:
        try:
            FastAPIInstrumentor.instrument_app(app)
        except Exception as exc:  # pragma: no cover
            logger.warning("FastAPI OTel instrumentation failed: %s", exc)
    try:
        import httpx
        if _OTEL_AVAILABLE:
            HTTPXClientInstrumentor().instrument()
    except Exception:
        pass