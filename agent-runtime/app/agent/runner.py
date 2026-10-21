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
        # 当前这次诊断的 checkpoint key（task-/manual- 级别）。
        # 同一 incident 的重诊必须换 key，否则第二轮会读到第一轮已完成结果。
        self._checkpoint_key: str | None = None
        if checkpoint_store:
            # P0-09: 每步落盘 —— 崩溃后可从最近一步续跑
            self.diagnostic.on_step = lambda s: checkpoint_store.save(
                self._checkpoint_key or s.incident_id, s)

    def run_diagnosis(self, incident_id: int, alert: dict,
                      run_key: str | None = None) -> AgentRunResult:
        start = time.perf_counter()
        resumed = False
        state = None
        # 未显式给 key 时保持旧行为（incident_id），兼容既有调用与测试；
        # consumer 必须传 task-<id>，手动入口传每次唯一的 manual-<uuid>。
        checkpoint_key = run_key or str(incident_id)
        self._checkpoint_key = checkpoint_key
        if self.checkpoint_store:
            saved = self.checkpoint_store.load(checkpoint_key)
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
            self.checkpoint_store.save(checkpoint_key, state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentRunResult(state=state, diagnosis=diagnosis, verification=None,
                              duration_ms=duration_ms, resumed=resumed)

    def run_verification(self, state: AgentState,
                         run_key: str | None = None) -> AgentRunResult:
        start = time.perf_counter()
        # 验证任务也按 task key 落盘；没有 key 时退回 incident_id，
        # 避免复用上一个诊断任务的 _checkpoint_key。
        self._checkpoint_key = run_key or str(state.incident_id)
        verification = self.verification.run(state)
        if self.checkpoint_store:
            self.checkpoint_store.save(self._checkpoint_key, state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentRunResult(state=state, diagnosis=state.diagnosis, verification=verification, duration_ms=duration_ms)
