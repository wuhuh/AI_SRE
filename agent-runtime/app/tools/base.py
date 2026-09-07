from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

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
        from concurrent.futures import ThreadPoolExecutor
        start = time.perf_counter()
        call = ToolCall(name=self.spec.name, arguments=arguments, status="SUCCESS")
        call.risk_level = self.spec.risk_level  # P2-CP-23: 风险随执行盖章
        try:
            if principal not in self.spec.allowed_principals:
                raise PermissionError(f"{principal} is not allowed to call {self.spec.name}")
            # P1-AR-07: 按 spec.timeout_seconds 强制超时（卡死的工具会耗尽诊断预算）。
            # wait=False：超时后不再等待卡死线程（Python 无法杀线程，本地 HTTP 工具会自行结束）
            pool = ThreadPoolExecutor(max_workers=1)
            future = pool.submit(self.execute, arguments, principal)
            try:
                result = future.result(timeout=self.spec.timeout_seconds)
            finally:
                pool.shutdown(wait=False)
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
        # P2-FI-08: 按最终状态计数（成功/超时/拒绝/错误）
        from app.metrics import TOOL_CALLS_TOTAL
        TOOL_CALLS_TOTAL.labels(tool=self.spec.name, status=call.status).inc()
        return call


class ReadOnlyTool(Tool):
    pass
