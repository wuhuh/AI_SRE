"""Tool Gateway.

Exposes safe, read-mostly tool endpoints for the agent runtime. Write tools are
only exposed to the control plane with the exact shared execution token
(X-Execution-Token header); token-in-URL and length-based bypasses are gone.
"""
from __future__ import annotations

import hmac
import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="AI SRE Tool Gateway", version="0.1.0")

APPROVAL_TOKEN = os.getenv("APPROVAL_TOKEN", "local-dev-token")
WRITE_ACTIONS = ("restart_pod", "scale_deployment", "delete_pod", "rollback_deployment")


def _token_ok(provided: str | None) -> bool:
    # P0-04: 精确匹配 + 常量时间比较（旧实现 len>=8 即放行等于没有校验）
    return bool(provided) and hmac.compare_digest(provided.encode(), APPROVAL_TOKEN.encode())


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
def kubernetes_read(action: str = "list_pods", namespace: str = "default") -> dict[str, Any]:
    # P0-04: GET 只保留只读 dryRun 操作；写操作必须走 POST + X-Execution-Token
    if action in WRITE_ACTIONS:
        raise HTTPException(status_code=405, detail="write actions require POST with X-Execution-Token")
    return {"action": action, "namespace": namespace, "dryRun": True}


@app.post("/api/k8s")
def kubernetes_write(payload: dict[str, Any],
                     x_execution_token: str | None = Header(default=None)) -> dict[str, Any]:
    action = str(payload.get("action", ""))
    if action not in WRITE_ACTIONS:
        raise HTTPException(status_code=400, detail=f"unknown or read-only action: {action}")
    if not _token_ok(x_execution_token):
        raise HTTPException(status_code=403, detail="invalid execution token")
    params = {k: v for k, v in payload.items() if k not in ("action", "namespace")}
    # P0-07: compose 演示挂载 docker.sock 时，restart_pod 真实重启容器；
    # 无 socket（k8s 环境）保持 dryRun，等 in-cluster ServiceAccount 接管（P0-10）
    if action == "restart_pod" and _docker_available():
        container = str(params.get("pod", ""))
        restarted = _docker_restart(container)
        if restarted:
            return {"action": action, "namespace": payload.get("namespace", "default"),
                    "params": params, "executed": True, "detail": restarted}
    return {"action": action, "namespace": payload.get("namespace", "default"),
            "params": params, "dryRun": True}


DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "")


def _docker_available() -> bool:
    return bool(DOCKER_SOCKET) and os.path.exists(DOCKER_SOCKET)


def _unix_http(request: str) -> tuple[str, bytes]:
    """经 docker.sock 发一次 HTTP/1.1，返回 (status, 解码 chunked 后的 body)。"""
    import socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(30)
    try:
        s.connect(DOCKER_SOCKET)
        s.sendall(request.encode())
        chunks = []
        while True:
            c = s.recv(65536)
            if not c:
                break
            chunks.append(c)
    finally:
        s.close()
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    status = head.split(b" ")[1].decode()
    if b"chunked" in head.lower():
        out = bytearray()
        while body:
            line, _, body = body.partition(b"\r\n")
            size = int(line.split(b";")[0], 16)
            if size == 0:
                break
            out.extend(body[:size])
            body = body[size + 2:]
        body = bytes(out)
    return status, body


def _docker_restart(container: str) -> str | None:
    """compose 演示模式：经 docker.sock 真实重启容器。"""
    try:
        from urllib.parse import quote
        filt = quote('{"name":["%s"]}' % container)
        status, body = _unix_http(f"GET /v1.43/containers/json?all=true&filters={filt} HTTP/1.1\r\nHost: docker\r\nConnection: close\r\n\r\n")
        if not status.startswith("2"):
            return None
        listed = json.loads(body.decode())
        if not listed:
            return None
        cid = listed[0]["Id"][:12]
        real_name = listed[0].get("Names", ["?"])[0].lstrip("/")
        status2, _ = _unix_http(f"POST /v1.43/containers/{cid}/restart HTTP/1.1\r\nHost: docker\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        return f"docker restart {real_name}: HTTP {status2}" if status2.startswith("2") else None
    except Exception:
        import traceback
        traceback.print_exc()
        return None


@app.get("/api/db")
def database(command: str = "health") -> dict[str, Any]:
    if command == "active_connections":
        return {"active_connections": 42}
    if command == "slow_query":
        return {"slow_queries": [{"query": "select * from orders", "duration_ms": 1200}]}
    if command == "explain_query":
        return {"plan": "Seq Scan on orders (cost=0.00..1.01 rows=1 width=16)"}
    return {"status": "ok", "database": os.getenv("DB_NAME", "aisre")}