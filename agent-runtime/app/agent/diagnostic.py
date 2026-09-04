from __future__ import annotations

import json

from app.context import build_context
from app.llm.base import LLMProvider, Message
from app.models import AgentState, DiagnosisResult, Evidence, ToolCall
from app.tools.registry import ToolRegistry

MAX_STEPS = 12

# P0-03: canonical RCA 标签空间（closed world，与 evaluation/cases 的 fault_type 对齐）。
# LLM 必须从该集合中输出 rootCause；alternatives 也取自该集合。
# 新增故障类别时同步扩展：evaluation/cases + 本列表 + runbook。
RCA_CANDIDATE_LABELS = (
    "cpu_saturation",
    "database_connection_pool_exhausted",
    "downstream_http_timeout",
    "memory_leak",
    "pod_crashloopbackoff",
    "redis_connection_pool_exhausted",
    "redis_slow_command",
    "rocketmq_message_backlog",
    "slow_sql",
    "thread_pool_exhausted",
)


def normalize_label(value: str | None) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

# P0-02(ponytail): 查询模板与 demo 实际暴露的指标对齐
# （demo-services/shared/observability.py: http_requests_total / http_request_duration_seconds）。
# 旧代码写死 payment-service + 一个 demo 里根本不存在的 Spring 指标名。
# 注意：PromQL 自带花括号，不能用 str.format —— 用 f-string 构造函数。
# 更多故障类别模板：评测重做(P0-03)后按 runbook 归类补充。
def prom_error_query(service: str) -> str:
    return f'rate(http_requests_total{{service="{service}",status=~"5.."}}[5m])'


def prom_latency_query(service: str) -> str:
    return (
        'histogram_quantile(0.95, sum by (le) (rate('
        f'http_request_duration_seconds_bucket{{service="{service}"}}[5m])))'
    )


def prom_query_for(alert: dict) -> str:
    service = str(alert.get("service") or "unknown-service")
    text = f"{alert.get('alertName', '')} {alert.get('summary', '')}".lower()
    latency_hints = ("latency", "p99", "p95", "slow", "timeout", "延迟")
    if any(hint in text for hint in latency_hints):
        return prom_latency_query(service)
    return prom_error_query(service)


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
                state.error = "diagnosis_timeout"
                return self._finalize(state, {
                    "rootCause": "unknown",
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
        state.error = "diagnosis_timeout"
        return self._finalize(state, {
            "rootCause": "unknown",
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
        args = self._tool_arguments(state, tool_name)
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
        labels = ", ".join(RCA_CANDIDATE_LABELS)
        prompt = (
            "Based on the collected evidence, either return a final diagnosis JSON "
            '({"rootCause": "<label>", "alternatives": ["<label>", "<label>"], '
            '"confidence": 0.0, "evidence": [], "recommendedActions": []}) '
            'or request one more tool ({"nextTool": "tool_name"}). Do not explain.\n'
            f"rootCause must be exactly one of these labels: [{labels}].\n"
            '"alternatives" lists up to 2 other plausible labels (may be empty).\n\n'
            + context.summary
        )
        try:
            result = self.llm.complete([Message(role="user", content=prompt)])
            state.llm_input_tokens += result.input_tokens
            state.llm_output_tokens += result.output_tokens
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
        root_cause = str(decision.get("rootCause") or "unknown").strip() or "unknown"
        recommended = list(decision.get("recommendedActions", []) or [])
        confidence = float(decision.get("confidence", 0.0))
        fallback_used = False
        heuristic_candidate = None
        status = "ROOT_CAUSE_FOUND"
        if root_cause == "unknown":
            # P0-01(ponytail): 规则兜底只作降级提示，不冒充根因、不改写置信度、不伪造证据。
            # 未知根因也不给修复建议，避免在不确定结论上触发自动修复。
            # 启发式何时可删：评测重做(P0-03)且真实 LLM 路径稳定后整体移除。
            rule_root, _ = self._rule_based_diagnosis(state)
            fallback_used = True
            heuristic_candidate = rule_root
            confidence = min(confidence, 0.3)
            recommended = []
            status = "UNKNOWN"
        # P0-03: Top-3 = root_cause + alternatives（归一化、去重、去 unknown、封顶 3）
        candidates: list[str] = []
        if fallback_used:
            if heuristic_candidate:
                candidates.append(normalize_label(heuristic_candidate))
        else:
            for alt in [root_cause, *(decision.get("alternatives") or [])]:
                label = normalize_label(alt)
                if label and label != "unknown" and label not in candidates:
                    candidates.append(label)
            candidates = candidates[:3]
        result = DiagnosisResult(
            root_cause=root_cause,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=recommended,
            tool_calls=state.tool_calls,
            status=status,
            fallback_used=fallback_used,
            heuristic_candidate=heuristic_candidate,
            candidate_root_causes=candidates,
            llm_input_tokens=state.llm_input_tokens,
            llm_output_tokens=state.llm_output_tokens,
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

    def _tool_arguments(self, state: AgentState, tool_name: str) -> dict:
        """P0-02: 工具参数来自告警对象（此前硬编码 payment-service + 固定 PromQL）。"""
        service = str(state.alert.get("service") or "unknown-service")
        if tool_name == "query_logs":
            return {"service": service, "limit": 100}
        if tool_name in ("query_prometheus", "prometheus"):
            return {"query": prom_query_for(state.alert)}
        if tool_name == "query_trace":
            return {"service": service, "limit": 20}
        if tool_name == "kubernetes":
            return {"action": "list_pods", "namespace": "default"}
        if tool_name == "redis":
            return {"command": "info"}
        if tool_name == "database":
            return {"command": "active_connections"}
        return {}