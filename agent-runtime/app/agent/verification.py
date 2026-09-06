from __future__ import annotations

import json
import time

from app.context import build_context
from app.llm.base import LLMProvider, Message
from app.models import AgentState, Evidence, VerificationResult
from app.tools.registry import ToolRegistry


class VerificationAgent:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, max_steps: int = 6,
                 max_duration_seconds: float = 12.0):
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.max_duration_seconds = max_duration_seconds

    def run(self, state: AgentState) -> VerificationResult:
        # P1-AR-06: 修复后先等观察窗再采 SLI（指标需要时间反映修复效果）；
        # 观察窗不计入诊断预算（预算从窗口结束后才开始计时）
        from app.agent import sli_verify
        window = sli_verify.observation_window_seconds()
        if window > 0:
            time.sleep(window)
        start_time = time.monotonic()
        checks = ["query_prometheus", "query_logs", "query_trace"]
        for tool_name in checks:
            if state.step >= self.max_steps:
                break
            if time.monotonic() - start_time > self.max_duration_seconds:
                break
            call = self.registry.call(tool_name, self._args(state, tool_name))
            state.tool_calls.append(call)
            state.tool_results[tool_name] = call.result_summary or call.error or ""
            state.step += 1
            if call.status == "SUCCESS":
                state.evidence.append(Evidence(
                    source=tool_name,
                    key=f"verify:{tool_name}",
                    content=call.result_summary[:500],
                ))

        # P1-AR-06: 确定性 SLI 判定——LLM 不再拥有恢复与否的决定权
        sli = self._measure_sli(state)
        determinate = sli_verify.judge(sli.get("error_rate"), sli.get("p95_seconds"))

        context = build_context(state, state.alert)
        prompt = (
            "Based on verification data, EXPLAIN the outcome only. "
            "The recovery decision is made by deterministic SLI thresholds, not by you. "
            'Return JSON {"detail": "..."}\n\n'
            + context.summary
        )
        try:
            result = self.llm.complete([Message(role="user", content=prompt)])
            data = json.loads(result.content)
        except Exception:
            data = {"detail": "LLM verification failed"}
        status = determinate if determinate != "UNKNOWN" else "UNKNOWN"
        if sli:
            state.evidence.append(Evidence(
                source="prometheus",
                key="sli",
                content=f"error_rate={sli.get('error_rate')},p95_seconds={sli.get('p95_seconds')}",
            ))
        verification = VerificationResult(status=status, detail=data.get("detail", ""),
                                          evidence=state.evidence, sli=sli)
        state.verification = verification
        state.status = "VERIFIED"
        return verification

    def _measure_sli(self, state: AgentState) -> dict[str, float]:
        """P1-AR-06: 采 error_rate 与 p95（无数据/不可达时字段缺省）。"""
        from app.agent.diagnostic import prom_error_query, prom_latency_query
        from app.agent.sli_verify import parse_instant_value

        service = str(state.alert.get("service") or "unknown-service")
        sli: dict[str, float] = {}
        for name, query in (("error_rate", prom_error_query(service)),
                            ("p95_seconds", prom_latency_query(service))):
            call = self.registry.call("query_prometheus", {"query": query})
            state.tool_calls.append(call)
            state.step += 1
            value = parse_instant_value(call.result_summary) if call.status == "SUCCESS" else None
            if value is not None:
                sli[name] = value
        return sli

    def _args(self, state, tool_name: str) -> dict:
        """P0-02: 验证阶段查询对准告警服务（此前硬编码 payment-service）。"""
        from app.agent.diagnostic import prom_error_query

        service = str(state.alert.get("service") or "unknown-service")
        if tool_name == "query_logs":
            return {"service": service, "limit": 50}
        if tool_name in ("query_prometheus", "prometheus"):
            return {"query": prom_error_query(service)}
        if tool_name == "query_trace":
            return {"service": service, "limit": 10}
        return {}
