from __future__ import annotations

import time
from dataclasses import dataclass

from app.agent.diagnostic import DiagnosticAgent
from app.agent.planner import Planner
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


class AgentRunner:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, retriever=None, checkpoint_store=None):
        self.planner = Planner(llm)
        self.diagnostic = DiagnosticAgent(llm, registry, retriever)
        self.verification = VerificationAgent(llm, registry)
        self.checkpoint_store = checkpoint_store

    def run_diagnosis(self, incident_id: int, alert: dict) -> AgentRunResult:
        state = AgentState(incident_id=incident_id, alert=alert, status="PLANNING")
        start = time.perf_counter()
        state.plan = self.planner.plan(state)
        state.status = "DIAGNOSING"
        diagnosis = self.diagnostic.run(state)
        if self.checkpoint_store:
            self.checkpoint_store.save(incident_id, state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentRunResult(state=state, diagnosis=diagnosis, verification=None, duration_ms=duration_ms)

    def run_verification(self, state: AgentState) -> AgentRunResult:
        start = time.perf_counter()
        verification = self.verification.run(state)
        if self.checkpoint_store:
            self.checkpoint_store.save(state.incident_id, state)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentRunResult(state=state, diagnosis=state.diagnosis, verification=verification, duration_ms=duration_ms)