"""Minimal MCP JSON-RPC client for the Tool Gateway."""
from __future__ import annotations

import json
import urllib.request
from typing import Any


class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8082"):
        self.base_url = base_url.rstrip("/")

    def _request(self, payload: dict[str, Any]) -> Any:
        req = urllib.request.Request(
            f"{self.base_url}/mcp",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_tools(self) -> list[dict[str, Any]]:
        data = self._request({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        return data.get("result", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        data = self._request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {"name": name, "arguments": arguments},
        })
        if "error" in data:
            raise RuntimeError(data["error"]["message"])
        return data.get("result")