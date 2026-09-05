from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

from app.tools.base import Tool, ToolSpec
from app.tools.policy import assert_namespace_allowed


def _http_get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


class PrometheusTool(Tool):
    spec = ToolSpec(
        name="query_prometheus",
        description="Query Prometheus metrics",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "step": {"type": "string"},
            },
            "required": ["query"],
        },
        risk_level="READ_ONLY",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")).rstrip("/")

    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        q = urllib.parse.quote(arguments["query"])
        url = f"{self.base_url}/api/v1/query?query={q}"
        if arguments.get("start"):
            url += f"&start={arguments['start']}"
        if arguments.get("end"):
            url += f"&end={arguments['end']}"
        if arguments.get("step"):
            url += f"&step={arguments['step']}"
        return json.dumps(_http_get_json(url), ensure_ascii=False)


class LogTool(Tool):
    spec = ToolSpec(
        name="query_logs",
        description="Query Loki logs by service, time range, traceId or keyword",
        parameters={
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "traceId": {"type": "string"},
                "keyword": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["service"],
        },
        risk_level="READ_ONLY",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("LOKI_URL", "http://localhost:3100")).rstrip("/")

    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        query = f'{{service="{arguments["service"]}"}}'
        if arguments.get("traceId"):
            query += f' |= "{arguments["traceId"]}"'
        if arguments.get("keyword"):
            query += f' |= "{arguments["keyword"]}"'
        params = {"query": query, "limit": arguments.get("limit", 100)}
        # P0-07: Loki API 不接受 "now-1h" 这类相对时间（400）——缺省即最近 1h，仅透传显式值
        if arguments.get("start") is not None:
            params["start"] = arguments["start"]
        if arguments.get("end") is not None:
            params["end"] = arguments["end"]
        url = f"{self.base_url}/loki/api/v1/query_range?{urllib.parse.urlencode(params)}"
        return json.dumps(_http_get_json(url), ensure_ascii=False)


class TraceTool(Tool):
    spec = ToolSpec(
        name="query_trace",
        description="Query traces by traceId or get slow traces",
        parameters={
            "type": "object",
            "properties": {
                "traceId": {"type": "string"},
                "service": {"type": "string"},
                "minDuration": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": [],
        },
        risk_level="READ_ONLY",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("TEMPO_URL", "http://localhost:3200")).rstrip("/")

    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        if arguments.get("traceId"):
            url = f"{self.base_url}/api/traces/{arguments['traceId']}"
        else:
            # P0-07: TEMPO_URL 实际指向 Jaeger all-in-one —— 用 Jaeger 的 /api/traces
            # （原 /api/search 是 Tempo 端点，Jaeger 上恒 404；tags=error=true
            #  是 Tempo 的键值语法，Jaeger 要求 JSON map，裸传直接 400——默认不带）
            params = urllib.parse.urlencode({
                "service": arguments.get("service", ""),
                "lookback": "1h",
                "limit": arguments.get("limit", 20),
            })
            url = f"{self.base_url}/api/traces?{params}"
        return json.dumps(_http_get_json(url), ensure_ascii=False)


class KubernetesTool(Tool):
    spec = ToolSpec(
        name="kubernetes",
        description="Read Kubernetes resources or execute controlled restart/scale",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_pods", "get_pod", "get_deployment", "get_events",
                             "get_pod_logs", "restart_pod", "scale_deployment"],
                },
                "namespace": {"type": "string"},
                "pod": {"type": "string"},
                "deployment": {"type": "string"},
                "replicas": {"type": "integer"},
            },
            "required": ["action"],
        },
        risk_level="READ_ONLY",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("KUBE_TOOL_URL", "http://localhost:8001")).rstrip("/")

    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        action = arguments["action"]
        if arguments.get("namespace"):
            assert_namespace_allowed(arguments["namespace"])
        risk_by_action = {
            "restart_pod": "LOW_RISK",
            "scale_deployment": "HIGH_RISK",
        }
        risk = risk_by_action.get(action, "READ_ONLY")
        if risk == "HIGH_RISK" and principal != "admin":
            raise PermissionError("scale_deployment requires admin approval")
        params = urllib.parse.urlencode(arguments)
        url = f"{self.base_url}/api/k8s?{params}"
        return json.dumps(_http_get_json(url), ensure_ascii=False)


class RedisTool(Tool):
    spec = ToolSpec(
        name="redis",
        description="Read Redis INFO, SLOWLOG and memory statistics",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": ["info", "slowlog", "memory"]},
                "host": {"type": "string"},
                "port": {"type": "integer"},
            },
            "required": ["command"],
        },
        risk_level="READ_ONLY",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("REDIS_TOOL_URL", "http://localhost:8002")).rstrip("/")

    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        params = urllib.parse.urlencode(arguments)
        url = f"{self.base_url}/api/redis?{params}"
        return json.dumps(_http_get_json(url), ensure_ascii=False)


class DatabaseTool(Tool):
    spec = ToolSpec(
        name="database",
        description="Read-only database health, connections and slow queries",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["health", "active_connections", "slow_query", "explain_query"],
                },
                "sql": {"type": "string"},
            },
            "required": ["command"],
        },
        risk_level="READ_ONLY",
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("DB_TOOL_URL", "http://localhost:8003")).rstrip("/")

    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        params = urllib.parse.urlencode(arguments)
        url = f"{self.base_url}/api/db?{params}"
        return json.dumps(_http_get_json(url), ensure_ascii=False)