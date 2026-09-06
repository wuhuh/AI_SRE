"""Checkpoint persistence for AgentState.

The production implementation would write to PostgreSQL; this first version uses
a JSON file store so the agent runtime can resume after a crash in local/dev mode.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.models import AgentState, Evidence, ToolCall

try:
    from app.models import DiagnosisResult, VerificationResult
except Exception:  # pragma: no cover
    DiagnosisResult = None
    VerificationResult = None


def _state_from_dict(data: dict) -> AgentState:
    tool_calls = [ToolCall(**t) for t in data.get("tool_calls", [])]
    evidence = [Evidence(**e) for e in data.get("evidence", [])]
    diagnosis = data.get("diagnosis")
    if isinstance(diagnosis, dict):
        diagnosis = DiagnosisResult(**diagnosis)
    verification = data.get("verification")
    if isinstance(verification, dict):
        verification = VerificationResult(**verification)
    return AgentState(
        incident_id=data.get("incident_id", 0),
        alert=data.get("alert", {}),
        plan=data.get("plan", []),
        pending=data.get("pending", []),
        tool_results=data.get("tool_results", {}),
        evidence=evidence,
        tool_calls=tool_calls,
        diagnosis=diagnosis,
        verification=verification,
        step=data.get("step", 0),
        status=data.get("status", "CREATED"),
        error=data.get("error"),
        llm_input_tokens=data.get("llm_input_tokens", 0),
        llm_output_tokens=data.get("llm_output_tokens", 0),
    )


class CheckpointStore:
    def save(self, incident_id: int, state: AgentState) -> None:
        raise NotImplementedError

    def load(self, incident_id: int) -> AgentState | None:
        raise NotImplementedError


class FileCheckpointStore(CheckpointStore):
    def __init__(self, base_dir: str | os.PathLike[str] | None = None):
        self.base_dir = Path(base_dir or os.getenv("CHECKPOINT_DIR", "checkpoints"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, incident_id: int, state: AgentState) -> None:
        # P0-09: tmp + os.replace 原子写 —— 崩溃不会留下半截 JSON
        path = self.base_dir / f"{incident_id}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state.to_dict(), ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def load(self, incident_id: int) -> AgentState | None:
        path = self.base_dir / f"{incident_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            # 半截/损坏文件当作无 checkpoint：宁可重跑，不要带病恢复
            return None
        try:
            return _state_from_dict(data)
        except TypeError:
            return None
