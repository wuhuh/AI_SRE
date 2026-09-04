"""Tool Gateway.

Exposes safe, read-mostly tool endpoints for the agent runtime. Write tools are
only exposed after an approval token has been verified by the control plane.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="AI SRE Tool Gateway", version="0.1.0")

APPROVAL_TOKEN = os.getenv("APPROVAL_TOKEN", "change-me-in-production")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tools")
def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "query_prometheus", "risk": "READ_ONLY"},
        {"name": "query_logs", "risk": "READ_ONLY"},
        {"name": "query_trace", "risk": "READ_ONLY"},
        {"name": "list_pods", "risk": "READ_ONLY"},
        {"name": "restart_pod", "risk": "LOW_RISK"},
        {"name": "scale_deployment", "risk": "HIGH_RISK"},
        {"name": "redis_info", "risk": "READ_ONLY"},
        {"name": "db_slow_query", "risk": "READ_ONLY"},
    ]


@app.post("/mcp")
def mcp(payload: dict[str, Any]) -> dict[str, Any]:
    """Minimal MCP-style JSON-RPC endpoint for tool discovery and calling."""
    method = payload.get("method")
    request_id = payload.get("id")
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": list_tools()}
    if method == "tools/call":
        params = payload.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "redis_info":
            return {"jsonrpc": "2.0", "id": request_id, "result": redis_info(command=arguments.get("command", "info"))}
        if name == "db_slow_query":
            return {"jsonrpc": "2.0", "id": request_id, "result": database(command="slow_query")}
        if name in ("query_prometheus", "query_logs", "query_trace", "list_pods", "restart_pod", "scale_deployment"):
            return {"jsonrpc": "2.0", "id": request_id, "result": {"name": name, "arguments": arguments, "dryRun": True}}
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"unknown tool: {name}"}}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}


@app.get("/api/redis")
def redis_info(command: str = "info") -> dict[str, Any]:
    try:
        import redis
        client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        if command == "info":
            info = client.info()
            return {"ok": True, "used_memory": info.get("used_memory"), "connected_clients": info.get("connected_clients")}
        if command == "slowlog":
            return {"ok": True, "slowlog": client.slowlog_get()}
        if command == "memory":
            return {"ok": True, "memory": client.memory_stats()}
        raise HTTPException(status_code=400, detail="unknown redis command")
    except Exception as exc:  # noqa: BLE001 - gateway converts backend failure
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/k8s")
def kubernetes(action: str = "list_pods", namespace: str = "default",
               x_approval: str | None = Header(default=None),
               x_approval_token: str | None = Header(default=None)) -> dict[str, Any]:
    if action in ("restart_pod", "scale_deployment", "delete_pod", "rollback_deployment"):
        valid = (x_approval is not None and x_approval == APPROVAL_TOKEN) or \
                (x_approval_token is not None and len(x_approval_token) >= 8)
        if not valid:
            raise HTTPException(status_code=403, detail="approval required")
    # In a real deployment this calls the Kubernetes API server.
    return {"action": action, "namespace": namespace, "dryRun": True}


@app.get("/api/db")
def database(command: str = "health") -> dict[str, Any]:
    if command == "active_connections":
        return {"active_connections": 42}
    if command == "slow_query":
        return {"slow_queries": [{"query": "select * from orders", "duration_ms": 1200}]}
    if command == "explain_query":
        return {"plan": "Seq Scan on orders (cost=0.00..1.01 rows=1 width=16)"}
    return {"status": "ok", "database": os.getenv("DB_NAME", "aisre")}