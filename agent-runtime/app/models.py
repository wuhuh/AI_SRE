"""Core data models for the AI SRE agent runtime.

Kept dependency-free on purpose so the core can be unit-tested without
installing FastAPI/Pydantic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    status: str = "PENDING"  # PENDING, SUCCESS, ERROR, TIMEOUT, DENIED
    result_summary: str = ""
    error: str | None = None
    duration_ms: int = 0


@dataclass
class Evidence:
    source: str
    key: str
    content: str


@dataclass
class DiagnosisResult:
    root_cause: str
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    status: str = "ROOT_CAUSE_FOUND"
    # P0-01: 规则兜底不再冒充结论，仅作为降级提示随结果透出
    fallback_used: bool = False
    heuristic_candidate: str | None = None
    # P0-03: 真实 Top-3 依据（root_cause + alternatives，归一化后去重，最多 3 个）
    candidate_root_causes: list[str] = field(default_factory=list)
    # P0-03: 真实 token 计量（openai provider 返回 usage；mock 为固定值）
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0


@dataclass
class VerificationResult:
    status: str  # RECOVERED, NOT_RECOVERED, UNKNOWN
    detail: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class AgentState:
    incident_id: int
    alert: dict[str, Any]
    plan: list[str] = field(default_factory=list)
    # P0-09: 剩余待执行步骤（随 checkpoint 持久化，崩溃后据此续跑）
    pending: list[str] = field(default_factory=list)
    tool_results: dict[str, str] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    diagnosis: DiagnosisResult | None = None
    verification: VerificationResult | None = None
    step: int = 0
    status: str = "CREATED"
    error: str | None = None
    # P0-03: 跨步累计 LLM token 用量
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMResult:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
