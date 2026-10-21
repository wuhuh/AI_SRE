from __future__ import annotations

import json
import logging
import time

from app.context import DATA_NOT_INSTRUCTIONS, build_context, wrap_evidence
from app.llm.base import LLMProvider, Message
from app.models import AgentState, DiagnosisResult, Evidence, LLMResult, ToolCall
from app.tools.policy import escape_label_value
from app.tools.registry import ToolRegistry

logger = logging.getLogger("agent.diagnostic")

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
    safe = escape_label_value(service)
    return f'rate(http_requests_total{{service="{safe}",status=~"5.."}}[5m])'


def prom_latency_query(service: str) -> str:
    safe = escape_label_value(service)
    return (
        'histogram_quantile(0.95, sum by (le) (rate('
        f'http_request_duration_seconds_bucket{{service="{safe}"}}[5m])))'
    )


def prom_traffic_query(service: str) -> str:
    """总请求速率（验证阶段用它判断窗口内流量样本是否充足——文档 11.3）。"""
    safe = escape_label_value(service)
    return f'sum(rate(http_requests_total{{service="{safe}"}}[5m]))'


def prom_query_for(alert: dict) -> str:
    service = str(alert.get("service") or "unknown-service")
    text = f"{alert.get('alertName', '')} {alert.get('summary', '')}".lower()
    latency_hints = ("latency", "p99", "p95", "slow", "timeout", "延迟")
    if any(hint in text for hint in latency_hints):
        return prom_latency_query(service)
    return prom_error_query(service)


class DiagnosticAgent:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, retriever=None,
                 max_steps: int = MAX_STEPS, max_duration_seconds: float = 15.0,
                 open_set: bool = False):
        self.llm = llm
        self.registry = registry
        self.retriever = retriever
        self.max_steps = max_steps
        self.max_duration_seconds = max_duration_seconds
        # 开放诊断：prompt 不提供候选标签，模型自由输出 label 或 unknown。
        # 生产默认 closed（CP 的 RcaLabels 契约）；评测可显式开启。
        self.open_set = open_set
        # P0-09: runner 注入的每步回调（落 checkpoint）；诊断循环每执行一步调用一次
        self.on_step = None

    def _checkpoint(self, state: AgentState) -> None:
        if self.on_step is not None:
            try:
                self.on_step(state)
            except Exception:
                pass  # checkpoint 失败不应中断诊断

    def run(self, state: AgentState) -> DiagnosisResult:
        start_time = time.monotonic()
        # P0-09: pending 存在 state 上（与 checkpoint 同持久化）——
        # 崩溃续跑时从剩余步骤继续，已完成工具不重复执行
        pending = state.pending or list(state.plan)
        state.pending = pending
        logger.info("diagnosis start: incident=%s plan=%s resumed_pending=%s",
                    state.incident_id, state.plan, bool(state.pending))
        unresolved = 0  # 连续不可解析 nextTool 计数（P0-08 收敛守卫）
        while state.step < self.max_steps:
            if time.monotonic() - start_time > self.max_duration_seconds:
                state.error = "diagnosis_timeout"
                return self._finalize(state, {
                    "rootCause": "unknown",
                    "confidence": 0.0,
                    "evidence": [],
                    "recommendedActions": [],
                }, timed_out=True)
            if pending:
                raw_tool = pending.pop(0)
                tool_name = self._normalize_tool_name(raw_tool)
                if tool_name is not None:
                    call = self._execute_tool(state, tool_name)
                    self._remember_legacy_tool_result(state, tool_name, call)
                    self._checkpoint(state)
                else:
                    # 红线 13 加固：计划里的步骤解析不出工具名时不能静默跳过——
                    # 那正是 retrieve_runbook 之前被丢掉、以及「固定 4 步实跑 3 步」
                    # 长期没被发现的原因。留一条 WARN 让缺口可观测。
                    logger.warning("plan step skipped: unresolvable tool %r (incident=%s)",
                                   raw_tool, state.incident_id)
                continue

            # 一次 LLM 调用：优先消费 native tool_calls；否则回退旧的 JSON 协议
            # （{"nextTool": ...} 或最终 diagnosis），保证 mock / 旧模型仍可工作。
            result = self._ask_llm(state)
            self._checkpoint(state)
            if result.tool_calls:
                self._handle_native_tool_calls(state, result)
                continue

            decision = self._parse_decision(state, result)
            if decision.get("nextTool"):
                next_tool = self._normalize_tool_name(decision["nextTool"])
                self._remember_assistant_message(state, result)
                if next_tool is not None:
                    pending.append(next_tool)
                    unresolved = 0
                else:
                    # P0-08: LLM 编造不存在的工具名（如 redis_info/get_container_metrics）
                    # 会让 pending 永远为空 → 空转烧满预算。已执行过工具仍收敛不了才强制出结论；
                    # 一个工具没跑过就收敛会让可观测的真实证据白白错过。
                    self._remember_tool_error(
                        state, f"unknown tool {decision['nextTool']!r}")
                    unresolved += 1
                    if unresolved >= 2 and state.tool_calls:
                        state.error = f"unresolvable_tool:{decision['nextTool']}"
                        return self._finalize(state, decision)
                continue
            return self._finalize(state, decision)

        # If we exhausted steps without a final answer, ask one more time for a graceful failure.
        if time.monotonic() - start_time <= self.max_duration_seconds:
            result = self._ask_llm(state)
            if result.tool_calls:
                state.error = "max_steps_reached_with_pending_tool_calls"
                return self._finalize(state, {
                    "rootCause": "unknown",
                    "confidence": 0.0,
                    "evidence": [],
                    "recommendedActions": [],
                })
            return self._finalize(state, self._parse_decision(state, result))
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
        # 红线 13/18：别名表必须先查，再回落到 registry 精确匹配。
        # 旧顺序是「先匹配 registry」，而 retrieve_runbook 不在 registry 里
        # （它由 retriever 在进程内实现，见 _execute_tool），于是
        # DEFAULT_PLAN 的第 4 步 `retrieve_runbook` 在别名表命中之前就返回 None
        # 被静默跳过 → 固定开局实际只跑 3 个只读工具。
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
            "redis_info": "redis",
            "redis-cli": "redis",
            "redis_cli": "redis",
            "query_redis": "redis",
            "redis_tool": "redis",
            "database": "database",
            "db": "database",
            "retrieve_runbook": "retrieve_runbook",
            "runbook": "retrieve_runbook",
            "rag": "retrieve_runbook",
        }
        if normalized in aliases:
            return aliases[normalized]
        if normalized in self.registry.names():
            return normalized
        return None

    def _tool_specs(self) -> list[dict]:
        """把 Tool Registry 转成 OpenAI function-calling schema。

        retrieve_runbook 由进程内 retriever 实现（不在 registry 里），
        这里补一条合成 schema，让模型也能主动请求 Runbook。
        """
        specs: list[dict] = []
        for s in self.registry.specs():
            specs.append({
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "parameters": s.get("parameters") or {"type": "object", "properties": {}},
                },
            })
        if "retrieve_runbook" not in {s["function"]["name"] for s in specs}:
            specs.append({
                "type": "function",
                "function": {
                    "name": "retrieve_runbook",
                    "description": "Retrieve runbooks/postmortems relevant to the incident",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": [],
                    },
                },
            })
        return specs

    def _tool_names(self) -> str:
        return ", ".join(s["function"]["name"] for s in self._tool_specs())

    def _diagnosis_instruction(self) -> str:
        if self.open_set:
            # 开放诊断：不泄漏候选标签空间。模型必须自己生成 label 或拒绝。
            return (
                "Based on the collected evidence, either return a final diagnosis JSON "
                '({"rootCause": "<label>", "alternatives": ["<label>", "<label>"], '
                '"confidence": 0.0, "evidence": [], "recommendedActions": []}) '
                'or request one more tool ({"nextTool": "tool_name"}). Do not explain.\n'
                "rootCause must be a concise snake_case label describing the most likely "
                "root cause, or 'unknown' if the evidence is insufficient to decide.\n"
                '"alternatives" lists up to 2 other plausible labels (may be empty).'
            )
        labels = ", ".join(RCA_CANDIDATE_LABELS)
        return (
            "Based on the collected evidence, either return a final diagnosis JSON "
            '({"rootCause": "<label>", "alternatives": ["<label>", "<label>"], '
            '"confidence": 0.0, "evidence": [], "recommendedActions": []}) '
            'or request one more tool ({"nextTool": "tool_name"}). Do not explain.\n'
            f"rootCause must be exactly one of these labels: [{labels}].\n"
            '"alternatives" lists up to 2 other plausible labels (may be empty).'
        )

    def _initial_user_content(self, state: AgentState) -> str:
        context = build_context(state, state.alert)
        return (
            f"{DATA_NOT_INSTRUCTIONS}\n"
            f"{self._diagnosis_instruction()}\n"
            f"Available tools: {self._tool_names()}\n\n"
            + context.summary
        )

    def _messages(self, state: AgentState) -> list[Message]:
        """初始化/恢复多轮消息；旧 checkpoint 没有 llm_messages 时用现有证据重建。"""
        if not state.llm_messages:
            state.llm_messages = [
                {"role": "system",
                 "content": "You are a precise SRE diagnostic agent. " + DATA_NOT_INSTRUCTIONS},
                {"role": "user", "content": self._initial_user_content(state)},
            ]
        return [
            Message(role=m.get("role", "user"), content=m.get("content") or "",
                    tool_call_id=m.get("tool_call_id"), tool_calls=m.get("tool_calls"))
            for m in state.llm_messages
        ]

    def _ask_llm(self, state: AgentState) -> LLMResult:
        """一次 LLM 调用：下发工具 schema，返回原始结果（tool_calls 由调用方消费）。"""
        try:
            result = self.llm.complete(self._messages(state), tools=self._tool_specs())
            state.llm_input_tokens += result.input_tokens
            state.llm_output_tokens += result.output_tokens
            return result
        except Exception as exc:
            logger.warning("llm decision failed: incident=%s error=%s", state.incident_id, exc)
            return LLMResult(content=json.dumps({
                "rootCause": "unknown",
                "confidence": 0.0,
                "evidence": [],
                "recommendedActions": [],
            }))

    def _parse_decision(self, state: AgentState, result: LLMResult) -> dict:
        try:
            decision = json.loads(result.content)
            if not isinstance(decision, dict):
                raise ValueError("decision must be a JSON object")
            # P0-07 排障：决策结果必须可见（LLM 回了什么、是否走降级）
            logger.info("llm decision: incident=%s root=%s nextTool=%s raw=%s",
                        state.incident_id, decision.get("rootCause"),
                        decision.get("nextTool"), result.content[:800])
            return decision
        except Exception as exc:
            logger.warning("llm decision parse failed: incident=%s error=%s", state.incident_id, exc)
            return {
                "rootCause": "unknown",
                "confidence": 0.0,
                "evidence": [],
                "recommendedActions": [],
            }

    def _remember_assistant_message(self, state: AgentState, result: LLMResult) -> None:
        if state.llm_messages:
            state.llm_messages.append({
                "role": "assistant",
                "content": result.content or "",
                "tool_calls": result.tool_calls or None,
            })

    def _remember_legacy_tool_result(self, state: AgentState, tool_name: str,
                                     call: ToolCall) -> None:
        """旧 JSON 协议（nextTool）下把工具结果作为下一条 user 消息回灌。"""
        if not state.llm_messages:
            return  # 固定初始计划阶段还没有会话，结果由首次 _initial_user_content 汇总
        body = (call.result_summary or call.error or "")[:4000]
        state.llm_messages.append({
            "role": "user",
            "content": f"{self._diagnosis_instruction()}\n\n"
                       f"Tool result for {tool_name}:\n{wrap_evidence(body)}",
        })

    def _remember_tool_error(self, state: AgentState, message: str) -> None:
        if state.llm_messages:
            state.llm_messages.append({
                "role": "user",
                "content": f"{self._diagnosis_instruction()}\n\nTool error: {message}\n"
                           f"Available tools: {self._tool_names()}",
            })

    @staticmethod
    def _parse_tool_arguments(raw) -> dict:
        """接受 OpenAI 的 JSON 字符串，也兼容部分代理直接回 dict。"""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                value = json.loads(raw)
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _handle_native_tool_calls(self, state: AgentState, result: LLMResult) -> None:
        """执行模型发起的 native tool_calls，并把结果写回消息历史。"""
        state.llm_messages.append({
            "role": "assistant",
            "content": result.content or "",
            "tool_calls": result.tool_calls,
        })
        for tc in result.tool_calls:
            if state.step >= self.max_steps:
                break
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function") or {}
            name = fn.get("name") if isinstance(fn, dict) else None
            raw_args = fn.get("arguments") if isinstance(fn, dict) else None
            call_id = tc.get("id") or f"call_{state.step}"
            tool_name = self._normalize_tool_name(name)
            if tool_name is None:
                state.llm_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": f"ERROR: unknown tool {name!r}. "
                               f"Available tools: {self._tool_names()}",
                })
                continue
            args = self._parse_tool_arguments(raw_args)
            call = self._execute_tool(state, tool_name, arguments=args)
            state.llm_messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": (call.result_summary or call.error or "")[:4000],
            })

    def _execute_tool(self, state: AgentState, tool_name: str,
                      arguments: dict | None = None) -> ToolCall:
        if tool_name == "retrieve_runbook":
            query = arguments.get("query") if isinstance(arguments, dict) else None
            self._retrieve_runbook(state, query=query)
            content = state.tool_results.get("retrieve_runbook", "")
            call = ToolCall(name="retrieve_runbook",
                            arguments={"query": query} if query else {},
                            status="SUCCESS", result_summary=content)
            state.tool_calls.append(call)
            state.step += 1
            return call
        # native tool_calls 的参数来自模型；只有旧 nextTool/固定计划才回退到告警驱动参数。
        args = arguments if isinstance(arguments, dict) else self._tool_arguments(state, tool_name)
        call = self.registry.call(tool_name, args)
        state.tool_calls.append(call)
        state.tool_results[tool_name] = call.result_summary or call.error or ""
        state.step += 1
        if call.status == "SUCCESS":
            # P2-AR-09: 证据带溯源（query/time_range），目前对查询类工具可填
            query = args.get("query") if isinstance(args, dict) else None
            time_range = None
            if query:
                import re as _re
                m = _re.search(r"\[(\w+)\]", query)
                time_range = m.group(1) if m else None
            state.evidence.append(Evidence(
                source=tool_name,
                key=f"{tool_name}:{state.step}",
                content=call.result_summary[:8000],
                query=query,
                time_range=time_range,
            ))
        return call

    def _retrieve_runbook(self, state: AgentState, query: str | None = None) -> None:
        if self.retriever is None:
            return
        effective_query = query or state.alert.get("summary", "")
        docs = self.retriever.retrieve(effective_query)
        content = "\n".join(f"[{d.id}] {d.title}: {d.content}" for d in docs)
        state.tool_results["retrieve_runbook"] = content[:8000]
        state.evidence.append(Evidence(
            source="rag",
            key="retrieved_runbooks",
            content=content[:8000],
            query=effective_query or None,
        ))

    def _finalize(self, state: AgentState, decision: dict, timed_out: bool = False) -> DiagnosisResult:
        evidence = state.evidence
        # P0-03: 真实 LLM 的输出形状多变 —— evidence 可能是字符串列表、
        # confidence 可能是字符串、alternatives 可能不是列表。全部宽容解析。
        raw_evidence = decision.get("evidence") or []
        if isinstance(raw_evidence, dict):
            raw_evidence = [raw_evidence]
        for e in raw_evidence:
            if isinstance(e, dict):
                evidence.append(Evidence(
                    source=str(e.get("source") or "llm"),
                    key=str(e.get("key") or "llm_evidence"),
                    content=str(e.get("content") or ""),
                ))
            elif e:
                evidence.append(Evidence(source="llm", key="llm_evidence", content=str(e)))
        root_cause = str(decision.get("rootCause") or "unknown").strip() or "unknown"
        recommended_raw = decision.get("recommendedActions") or []
        if isinstance(recommended_raw, str):
            recommended_raw = [recommended_raw]
        recommended = [str(a) for a in recommended_raw]
        try:
            confidence = float(decision.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        fallback_used = False
        heuristic_candidate = None
        reason_code = ""
        # P2-AR-09: status 语义——ROOT_CAUSE_FOUND / UNKNOWN（降级）/ TIMEOUT（预算耗尽）
        if timed_out:
            status = "TIMEOUT"
            reason_code = "timeout"
        else:
            status = "ROOT_CAUSE_FOUND"
        # 文档 8.6：闭集不能只靠提示约束——代码必须校验。
        # 模型编出的非法标签（不在 RCA_CANDIDATE_LABELS 内、也不是 unknown）
        # 不能因为「不是 unknown 字符串」就被视为已找到根因，
        # 走与 unknown 相同的降级路径（文档 8.5：同时清理没有依据的动作建议）。
        normalized_root = normalize_label(root_cause)
        valid_labels = {normalize_label(x) for x in RCA_CANDIDATE_LABELS}
        # 开放诊断不校验闭集：模型可以输出训练集之外的合理 label。
        invalid_label = (not self.open_set and not timed_out
                         and normalized_root != "unknown"
                         and normalized_root not in valid_labels)
        if self.open_set and not normalized_root:
            root_cause = "unknown"
        if invalid_label:
            logger.warning("model returned non-contract root label %r — treating as unknown", root_cause)
            root_cause = "unknown"
            reason_code = "invalid_label"
        if root_cause == "unknown" and not timed_out:
            # P0-01(ponytail): 规则兜底只作降级提示，不冒充根因、不改写置信度、不伪造证据。
            # 未知根因也不给修复建议，避免在不确定结论上触发自动修复。
            # 启发式何时可删：评测重做(P0-03)且真实 LLM 路径稳定后整体移除。
            rule_root, _ = self._rule_based_diagnosis(state)
            fallback_used = True
            heuristic_candidate = rule_root
            confidence = min(confidence, 0.3)
            recommended = []
            status = "UNKNOWN"
            if not reason_code:
                reason_code = "model_unknown"
        # P0-03: Top-3 = root_cause + alternatives（归一化、去重、去 unknown、封顶 3）
        candidates: list[str] = []
        if fallback_used:
            if heuristic_candidate:
                candidates.append(normalize_label(heuristic_candidate))
        else:
            alternatives = decision.get("alternatives") or []
            if isinstance(alternatives, str):
                alternatives = [alternatives]
            for alt in [root_cause, *alternatives]:
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
            reason_code=reason_code,
        )
        state.diagnosis = result
        state.status = "DIAGNOSED"
        # P0-07 排障：最终结论/降级/步数/耗时一屏可见
        logger.info("diagnosis finalize: incident=%s root=%s fallback=%s heuristic=%s steps=%s evidence=%s",
                    state.incident_id, result.root_cause, result.fallback_used,
                    result.heuristic_candidate, state.step, len(result.evidence))
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
