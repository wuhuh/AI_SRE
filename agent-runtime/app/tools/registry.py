from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.models import ToolCall
from app.tools.base import Tool


class ToolRegistry:
    """Explicit tool registry with permission, parameter validation and rate limiting."""

    def __init__(self, rate_limit_per_minute: int = 120):
        self._tools: dict[str, Tool] = {}
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._rate_limit_per_minute = rate_limit_per_minute

    def register(self, tool: Tool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.spec.name}")
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def specs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.spec.name,
                "description": t.spec.description,
                "parameters": t.spec.parameters,
                "risk_level": t.spec.risk_level,
                "timeout_seconds": t.spec.timeout_seconds,
            }
            for t in self._tools.values()
        ]

    def call(self, name: str, arguments: dict[str, Any], principal: str = "agent") -> ToolCall:
        tool = self._tools.get(name)
        if tool is None:
            return ToolCall(name=name, arguments=arguments, status="ERROR", error=f"Unknown tool: {name}")
        try:
            self._check_rate_limit(name)
            validated = self._validate(tool.spec.name, tool.spec.parameters, arguments)
            return tool.call(validated, principal=principal)
        except PermissionError as e:
            return ToolCall(name=name, arguments=arguments, status="DENIED", error=str(e))
        except Exception as e:  # noqa: BLE001 - argument errors become structured tool failures
            return ToolCall(name=name, arguments=arguments, status="ERROR", error=str(e))

    def _check_rate_limit(self, name: str) -> None:
        import time
        now = time.monotonic()
        q = self._calls[name]
        while q and now - q[0] > 60.0:
            q.popleft()
        if len(q) >= self._rate_limit_per_minute:
            raise PermissionError(f"Rate limit exceeded for tool {name}")
        q.append(now)

    def _validate(self, name: str, schema: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [r for r in required if r not in args]
        if missing:
            raise ValueError(f"Missing required arguments for {name}: {missing}")
        for key, value in args.items():
            prop = properties.get(key)
            if prop is None:
                continue
            expected_type = prop.get("type")
            if expected_type == "string" and not isinstance(value, str):
                raise ValueError(f"Argument {key} must be string")
            if expected_type == "integer" and not isinstance(value, int):
                raise ValueError(f"Argument {key} must be integer")
            if expected_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Argument {key} must be number")
        return args