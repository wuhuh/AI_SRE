from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from app.models import ToolCall


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "READ_ONLY"  # READ_ONLY | LOW_RISK | HIGH_RISK
    timeout_seconds: float = 10.0
    allowed_principals: list[str] = field(default_factory=lambda: ["admin", "agent"])


class Tool(ABC):
    spec: ToolSpec

    @abstractmethod
    def execute(self, arguments: dict[str, Any], principal: str = "agent") -> str:
        raise NotImplementedError

    def call(self, arguments: dict[str, Any], principal: str = "agent") -> ToolCall:
        import time
        start = time.perf_counter()
        call = ToolCall(name=self.spec.name, arguments=arguments, status="SUCCESS")
        try:
            if principal not in self.spec.allowed_principals:
                raise PermissionError(f"{principal} is not allowed to call {self.spec.name}")
            result = self.execute(arguments, principal=principal)
            call.result_summary = str(result)[:2000]
        except TimeoutError:
            call.status = "TIMEOUT"
            call.error = "tool timeout"
        except PermissionError as e:
            call.status = "DENIED"
            call.error = str(e)
        except Exception as e:  # noqa: BLE001 - converted to structured error for agent
            call.status = "ERROR"
            call.error = str(e)
        finally:
            call.duration_ms = int((time.perf_counter() - start) * 1000)
        return call


class ReadOnlyTool(Tool):
    pass