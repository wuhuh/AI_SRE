"""Tool policy: allowlists for namespaces, databases and services."""
from __future__ import annotations

ALLOWED_NAMESPACES = {"default", "ai-sre-demo", "ai-sre"}
ALLOWED_DATABASES = {"aisre", "demo"}
ALLOWED_SERVICES = {
    "api-gateway",
    "order-service",
    "inventory-service",
    "payment-service",
}


def assert_namespace_allowed(namespace: str) -> None:
    if namespace not in ALLOWED_NAMESPACES:
        raise PermissionError(f"namespace not allowed: {namespace}")


def assert_database_allowed(database: str) -> None:
    if database not in ALLOWED_DATABASES:
        raise PermissionError(f"database not allowed: {database}")


def assert_service_allowed(service: str) -> None:
    if service not in ALLOWED_SERVICES:
        raise PermissionError(f"service not allowed: {service}")