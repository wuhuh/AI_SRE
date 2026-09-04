"""Core data models for the AI SRE agent runtime.

Kept dependency-free on purpose so the core can be unit-tested without
installing FastAPI/Pydantic.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    status: str = "PENDING"  # PENDING, SUCCESS, ERROR, TIMEOUT, DENIED
    result_summary: str = ""
    error: Optional[str] = None
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
    tool_results: dict[str, str] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    diagnosis: Optional[DiagnosisResult] = None
    verification: Optional[VerificationResult] = None
    step: int = 0
    status: str = "CREATED"
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMResult:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)