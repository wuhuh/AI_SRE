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

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="AI SRE Tool Gateway", version="0.1.0")

APPROVAL_TOKEN = os.getenv("APPROVAL_TOKEN", "local-dev-token")
WRITE_ACTIONS = ("restart_pod", "scale_deployment", "delete_pod", "rollback_deployment")


def _token_ok(provided: str | None) -> bool:
    # P0-04: 精确匹配 + 常量时间比较（旧实现 len>=8 即放行等于没有校验）
    return bool(provided) and hmac.compare_digest(provided.encode(), APPROVAL_TOKEN.encode())


# P2-FI-08: 平台自监控（同端口 /metrics + 请求计数）
from prometheus_client import Counter as _Counter
from prometheus_client import make_asgi_app

TOOLSERVER_REQUESTS = _Counter(
    "aisre_toolserver_requests_total", "请求计数", ["path", "status"]
)


@app.middleware("http")
async def _count_requests(request, call_next):
    response = await call_next(request)
    TOOLSERVER_REQUESTS.labels(path=request.url.path, status=str(response.status_code)).inc()
    return response


app.mount("/metrics", make_asgi_app())


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
        if name == "list_pods":
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": kubernetes_read("list_pods", arguments.get("namespace", "default"))}
        if name in ("query_prometheus", "query_logs", "query_trace", "restart_pod", "scale_deployment"):
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


def _k8s_incluster_get(path: str) -> tuple[int, dict[str, Any]]:
    """P0-10: in-cluster ServiceAccount 直连 K8S API（标准库，不引 kubernetes 包）。

    返回 (status, body)；任何网络/证书问题向上抛由调用方决定回退。
    """
    import ssl
    import urllib.error
    import urllib.request

    sa = "/var/run/secrets/kubernetes.io/serviceaccount"
    with open(f"{sa}/token") as f:
        token = f.read().strip()
    req = urllib.request.Request(
        f"https://kubernetes.default.svc{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(cafile=f"{sa}/ca.crt"), timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def _incluster_namespace() -> str:
    """当前 Pod 所在 ns（SA namespace 文件）；读不到回退 ai-sre。"""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip()
    except OSError:
        return "ai-sre"


@app.get("/api/k8s")
def kubernetes_read(action: str = "list_pods", namespace: str = "default") -> dict[str, Any]:
    # P0-04: GET 只保留只读 dryRun 操作；写操作必须走 POST + X-Execution-Token
    if action in WRITE_ACTIONS:
        raise HTTPException(status_code=405, detail="write actions require POST with X-Execution-Token")
    # P0-10: in-cluster ServiceAccount 真实读取（SA 文件存在即 k8s 环境，优先于 docker）
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        ns = namespace if namespace != "default" else _incluster_namespace()
        try:
            if action == "list_pods":
                status, body = _k8s_incluster_get(f"/api/v1/namespaces/{ns}/pods")
                if status == 200:
                    pods = []
                    for item in body.get("items", []):
                        md = item["metadata"]
                        cs = (item.get("spec", {}) or {}).get("containers") or [{}]
                        pods.append({
                            "name": md["name"],
                            "podName": md["name"],
                            "status": (item.get("status", {}) or {}).get("phase", ""),
                            "image": (cs[0] or {}).get("image", ""),
                        })
                    return {"action": action, "namespace": ns, "pods": pods, "source": "in-cluster-k8s"}
                return {"action": action, "namespace": ns, "dryRun": True, "detail": f"k8s api status {status}"}
            return {"action": action, "namespace": ns, "dryRun": True,
                    "detail": f"read action {action} not implemented over in-cluster SA yet"}
        except Exception as exc:  # noqa: BLE001 — 失败回退 dryRun，但如实带上错误
            return {"action": action, "namespace": ns, "dryRun": True, "detail": f"k8s read failed: {exc}"}
    # P0-10 (compose 模式)：list_pods 用 docker ps 返回真实容器清单（等价 pod 视图）
    if action == "list_pods" and _docker_available():
        try:
            status, body = _unix_http("GET /v1.43/containers/json HTTP/1.1\r\nHost: docker\r\nConnection: close\r\n\r\n")
            if status.startswith("2"):
                pods = []
                for c in json.loads(body.decode()):
                    names = c.get("Names") or []
                    name = names[0].lstrip("/") if names else c.get("Id", "")[:12]
                    compose_service = (c.get("Labels") or {}).get("com.docker.compose.service")
                    pods.append({
                        "name": name,
                        "podName": compose_service or name,
                        "status": "Running" if c.get("State") == "running" else c.get("State", ""),
                        "image": c.get("Image", ""),
                    })
                return {"action": action, "namespace": namespace, "pods": pods, "source": "docker-compose"}
        except Exception as exc:  # noqa: BLE001 — 失败回退 dryRun，但如实带上错误
            return {"action": action, "namespace": namespace, "dryRun": True,
                    "detail": f"docker list failed: {exc}"}
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


DATABASE_DSN = os.getenv("DATABASE_DSN", "")


def _db_query(sql: str) -> list[dict[str, Any]]:
    """P0-10: 只读连接跑真实查询（会话级 read-only，双保险防写）。"""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(DATABASE_DSN, connect_timeout=5,
                            options="-c default_transaction_read_only=on")
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@app.get("/api/db")
def database(command: str = "health") -> dict[str, Any]:
    # P0-10: 真实只读查询（原 42/slow_query/explain 全是硬编码假数据）。
    # 无 DSN（如纯 k8s 环境）时如实报错，不再返回编造数字。
    if not DATABASE_DSN:
        raise HTTPException(status_code=503, detail="DATABASE_DSN not configured")
    try:
        if command == "health":
            rows = _db_query("SELECT 1 AS ok, version() AS version")
            return {"ok": True, "database": rows[0]["version"].split()[0]}
        if command == "active_connections":
            rows = _db_query(
                "SELECT count(*) AS active_connections, "
                "count(*) FILTER (WHERE state = 'active') AS running "
                "FROM pg_stat_activity")
            return {"ok": True, "active_connections": rows[0]["active_connections"],
                    "running": rows[0]["running"]}
        if command == "slow_query":
            rows = _db_query(
                "SELECT pid, usename, state, "
                "EXTRACT(epoch FROM now() - query_start) * 1000 AS duration_ms, "
                "left(query, 120) AS query FROM pg_stat_activity "
                "WHERE state <> 'idle' AND query NOT LIKE '%pg_stat_activity%' "
                "AND now() - query_start > interval '1 second' "
                "ORDER BY query_start LIMIT 10")
            return {"ok": True, "slow_queries": rows}
        if command == "explain_query":
            # 只读会话内 EXPLAIN 合法；query 参数由调用方给出，默认示例
            return {"ok": True, "note": "pass ?sql= for EXPLAIN"}
        raise HTTPException(status_code=400, detail=f"unknown db command: {command}")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — 真实错误如实返回，不吞
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
