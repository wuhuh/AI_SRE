from __future__ import annotations

import time
from dataclasses import dataclass

from app.agent.diagnostic import MAX_STEPS, DiagnosticAgent
from app.agent.planner import DEFAULT_PLAN
from app.agent.verification import VerificationAgent
from app.llm.base import LLMProvider
from app.models import AgentState, DiagnosisResult, VerificationResult
from app.tools.registry import ToolRegistry


@dataclass
class AgentRunResult:
    state: AgentState
    diagnosis: DiagnosisResult
    verification: VerificationResult | None
    duration_ms: int
    resumed: bool = False


class AgentRunner:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, retriever=None, checkpoint_store=None,
                 max_steps: int = MAX_STEPS, max_duration_seconds: float = 15.0):
        # P0-03: 预算可调 —— 慢 LLM/慢工具下默认 15s 会把大部分诊断打成超时降级
        self.diagnostic = DiagnosticAgent(llm, registry, retriever,
                                          max_steps=max_steps, max_duration_seconds=max_duration_seconds)
        self.verification = VerificationAgent(llm, registry)
        self.checkpoint_store = checkpoint_store
        if checkpoint_store:
            # P0-09: 每步落盘 —— 崩溃后可从最近一步续跑
            self.diagnostic.on_step = lambda s: checkpoint_store.save(s.incident_id, s)

    def run_diagnosis(self, incident_id: int, alert: dict) -> AgentRunResult:
        start = time.perf_counter()
        resumed = False
        state = None
        if self.checkpoint_store:
            saved = self.checkpoint_store.load(incident_id)
            if saved is not None:
                if saved.diagnosis is not None:
                    # P0-09: 已完成的诊断直接返回 —— 幂等，不再重复消耗 LLM
                    return AgentRunResult(state=saved, diagnosis=saved.diagnosis,
                                          verification=None, duration_ms=0, resumed=True)
                # 崩溃中断：从剩余 pending 续跑（已完成工具不重复执行）
                state = saved
                state.status = "DIAGNOSING"
                resumed = True
        if state is None:
            state = AgentState(incident_id=incident_id, alert=alert, status="PLANNING")
            # P2-AR-10: 固定初始计划（原 Planner 用 LLM 预规划属装饰调用——
            # 与逐步 LLM 决策重复，且其输出未经校验。真规划随 function calling 方案重做）
            state.plan = list(DEFAULT_PLAN)
            state.status = "DIAGNOSING"
        diagnosis = self.diagnostic.run(state)
        state.status = "DIAGNOSIS_COMPLETE"
        if self.checkpoint_store:
            self.checkpoint_store.save(incident_id, state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentRunResult(state=state, diagnosis=diagnosis, verification=None,
                              duration_ms=duration_ms, resumed=resumed)

    def run_verification(self, state: AgentState) -> AgentRunResult:
        start = time.perf_counter()
        verification = self.verification.run(state)
        if self.checkpoint_store:
            self.checkpoint_store.save(state.incident_id, state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentRunResult(state=state, diagnosis=state.diagnosis, verification=verification, duration_ms=duration_ms)
