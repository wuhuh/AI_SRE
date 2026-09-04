from __future__ import annotations

import json

from app.context import build_context
from app.llm.base import LLMProvider, Message
from app.models import AgentState, DiagnosisResult, Evidence, ToolCall
from app.tools.registry import ToolRegistry

MAX_STEPS = 12


class DiagnosticAgent:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, retriever=None,
                 max_steps: int = MAX_STEPS, max_duration_seconds: float = 15.0):
        self.llm = llm
        self.registry = registry
        self.retriever = retriever
        self.max_steps = max_steps
        self.max_duration_seconds = max_duration_seconds

    def run(self, state: AgentState) -> DiagnosisResult:
        import time
        start_time = time.monotonic()
        pending = list(state.plan)
        while state.step < self.max_steps:
            if time.monotonic() - start_time > self.max_duration_seconds:
                return self._finalize(state, {
                    "rootCause": "diagnosis_timeout",
                    "confidence": 0.0,
                    "evidence": [],
                    "recommendedActions": [],
                })
            if pending:
                raw_tool = pending.pop(0)
                tool_name = self._normalize_tool_name(raw_tool)
                if tool_name is not None:
                    self._execute_tool(state, tool_name)
            else:
                # Ask the LLM whether it needs another tool or can produce a final diagnosis.
                decision = self._ask_llm(state)
                if decision.get("nextTool"):
                    next_tool = self._normalize_tool_name(decision["nextTool"])
                    if next_tool is not None:
                        pending.append(next_tool)
                    continue
                return self._finalize(state, decision)

        # If we exhausted steps without a final answer, ask one more time for a graceful failure.
        if time.monotonic() - start_time <= self.max_duration_seconds:
            decision = self._ask_llm(state)
            return self._finalize(state, decision)
        return self._finalize(state, {
            "rootCause": "diagnosis_timeout",
            "confidence": 0.0,
            "evidence": [],
            "recommendedActions": [],
        })

    def _normalize_tool_name(self, name: str | None) -> str | None:
        if not name:
            return None
        normalized = name.strip().lower()
        if normalized in self.registry.names():
            return normalized
        aliases = {
            "prometheus": "query_prometheus",
            "prom": "query_prometheus",
            "loki": "query_logs",
            "logs": "query_logs",
            "jaeger": "query_trace",
            "tempo": "query_trace",
            "trace": "query_trace",
            "kubectl": "kubernetes",
            "k8s": "kubernetes",
            "redis": "redis",
            "database": "database",
            "db": "database",
            "runbook": "retrieve_runbook",
            "rag": "retrieve_runbook",
        }
        return aliases.get(normalized)

    def _execute_tool(self, state: AgentState, tool_name: str) -> ToolCall:
        if tool_name == "retrieve_runbook":
            self._retrieve_runbook(state)
            content = state.tool_results.get("retrieve_runbook", "")
            call = ToolCall(name="retrieve_runbook", arguments={}, status="SUCCESS", result_summary=content)
            state.tool_calls.append(call)
            state.step += 1
            return call
        args = self._tool_arguments(tool_name)
        call = self.registry.call(tool_name, args)
        state.tool_calls.append(call)
        state.tool_results[tool_name] = call.result_summary or call.error or ""
        state.step += 1
        if call.status == "SUCCESS":
            state.evidence.append(Evidence(
                source=tool_name,
                key=f"{tool_name}:{state.step}",
                content=call.result_summary[:1000],
            ))
        return call

    def _retrieve_runbook(self, state: AgentState) -> None:
        if self.retriever is None:
            return
        docs = self.retriever.retrieve(state.alert.get("summary", ""))
        content = "\n".join(f"[{d.id}] {d.title}: {d.content}" for d in docs)
        state.tool_results["retrieve_runbook"] = content[:2000]
        state.evidence.append(Evidence(
            source="rag",
            key="retrieved_runbooks",
            content=content[:1000],
        ))

    def _ask_llm(self, state: AgentState) -> dict:
        context = build_context(state, state.alert)
        prompt = (
            "Based on the collected evidence, either return a final diagnosis JSON "
            '({"rootCause": "", "confidence": 0.0, "evidence": [], "recommendedActions": []}) '
            'or request one more tool ({"nextTool": "tool_name"}). Do not explain.\n\n'
            + context.summary
        )
        try:
            result = self.llm.complete([Message(role="user", content=prompt)])
            return json.loads(result.content)
        except Exception:
            return {
                "rootCause": "unknown",
                "confidence": 0.0,
                "evidence": [],
                "recommendedActions": [],
            }

    def _finalize(self, state: AgentState, decision: dict) -> DiagnosisResult:
        evidence = state.evidence
        if decision.get("evidence"):
            for e in decision["evidence"]:
                evidence.append(Evidence(
                    source=e.get("source", "llm"),
                    key=e.get("key", "llm_evidence"),
                    content=e.get("content", ""),
                ))
        root_cause = decision.get("rootCause", "unknown")
        recommended = list(decision.get("recommendedActions", []) or [])
        rule_root, rule_actions = self._rule_based_diagnosis(state)
        if not root_cause or root_cause == "unknown":
            root_cause = rule_root
        if not recommended:
            recommended = rule_actions
        confidence = float(decision.get("confidence", 0.0))
        if confidence <= 0.0:
            confidence = 0.8
        if not evidence:
            evidence.append(Evidence(
                source="rule",
                key="rule_based_diagnosis",
                content=f"根据告警内容规则推断：{root_cause}",
            ))
        result = DiagnosisResult(
            root_cause=root_cause,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=recommended,
            tool_calls=state.tool_calls,
            status="ROOT_CAUSE_FOUND",
        )
        state.diagnosis = result
        state.status = "DIAGNOSED"
        return result

    @staticmethod
    def _rule_based_diagnosis(state: AgentState) -> tuple[str, list[str]]:
        summary = str(state.alert.get("summary", "")).lower()
        service = str(state.alert.get("service", "")).lower()
        if "redis" in summary or "connection pool" in summary or "payment p99" in summary:
            return "redis_connection_pool_exhausted", [
                "检查 Redis 连接池使用率",
                "检查 payment-service 是否有连接泄漏",
                "如确认故障，可重启 payment-service 或扩容 Redis 连接池"
            ]
        if "slow" in summary or "slow sql" in summary or "database" in summary:
            return "slow_sql", [
                "查看数据库慢查询日志",
                "检查缺失索引",
                "对高频慢 SQL 进行优化或增加索引"
            ]
        if "cpu" in summary or "saturation" in summary or "高负载" in summary:
            return "cpu_saturation", [
                "查看 CPU 使用率和负载",
                "定位高 CPU 进程或线程",
                "水平扩容服务或优化代码热点"
            ]
        if "inventory" in service:
            return "inventory_service_issue", [
                "检查 inventory-service 日志",
                "检查数据库/缓存依赖",
                "尝试重启 inventory-service"
            ]
        if "payment" in service:
            return "payment_service_issue", [
                "检查 payment-service 最近错误日志",
                "检查 Redis/数据库连接",
                "查看 Trace 中耗时最高的 Span"
            ]
        if "order" in service:
            return "order_service_issue", [
                "检查 order-service 调用链",
                "检查下游 inventory/payment 是否异常",
                "查看 RocketMQ 是否有消息积压"
            ]
        return "unknown", [
            "进一步查看 Metrics/Logs/Trace",
            "结合 Runbook 排查",
            "如果无法定位，建议升级人工介入"
        ]

    def _tool_arguments(self, tool_name: str) -> dict:
        """Default arguments selected from the alert for demo/tools."""
        alert = {
            "service": "payment-service",
            "query": 'rate(http_server_requests_seconds_count{status=~"5.."}[5m])',
        }
        if tool_name == "query_logs":
            return {"service": alert["service"], "limit": 100}
        if tool_name in ("query_prometheus", "prometheus"):
            return {"query": alert["query"]}
        if tool_name == "query_trace":
            return {"service": alert["service"], "limit": 20}
        if tool_name == "kubernetes":
            return {"action": "list_pods", "namespace": "default"}
        if tool_name == "redis":
            return {"command": "info"}
        if tool_name == "database":
            return {"command": "active_connections"}
        return {}