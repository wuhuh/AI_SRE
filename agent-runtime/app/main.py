from __future__ import annotations

import json
import logging
import os
import threading

# uvicorn 只配自己的 logger，root 仍是 WARNING——诊断关键路径的 INFO 会丢
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
from dataclasses import asdict
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.runner import AgentRunner
from app.checkpoint import FileCheckpointStore
from app.consumer import agent_headers, consumer_loop
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleLLMProvider
from app.llm.retry import RetryLLMProvider
from app.models import AgentState
from app.rag.retriever import Document, HybridRetriever
from app.tools.factory import create_default_registry

app = FastAPI(title="AI SRE Agent Runtime", version="0.1.0")


class DiagnoseRequest(BaseModel):
    incident_id: int
    alert: dict[str, Any]


class VerifyRequest(BaseModel):
    incident_id: int
    alert: dict[str, Any]


def _load_runbook_docs() -> list[Document]:
    # In a real deployment these docs are loaded from PostgreSQL/pgvector or disk.
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge-base", "runbooks")
    docs = []
    if os.path.isdir(base_dir):
        for name in sorted(os.listdir(base_dir)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(base_dir, name)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            docs.append(Document(id=name, title=name.replace("-", " "), content=content))
    return docs


def _build_runner() -> AgentRunner:
    if os.getenv("LLM_PROVIDER", "mock") == "openai":
        # P1-AR-04: 重试边界——429 尊重 Retry-After（封顶），5xx 短退避，4xx 直接上抛
        llm = RetryLLMProvider(
            OpenAICompatibleLLMProvider(),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
            delay_seconds=float(os.getenv("LLM_RETRY_DELAY_SECONDS", "0.5")),
        )
    else:
        llm = MockLLMProvider()
    registry = create_default_registry()
    retriever = HybridRetriever(_load_runbook_docs())
    checkpoint_store = FileCheckpointStore() if os.getenv("CHECKPOINT_DIR") else None
    # P0-03: 诊断预算/步数可用环境变量调（默认与原行为一致）
    try:
        budget = float(os.getenv("DIAG_BUDGET_SECONDS", "15"))
        max_steps = int(os.getenv("DIAG_MAX_STEPS", "12"))
    except ValueError:
        budget, max_steps = 15.0, 12
    return AgentRunner(llm=llm, registry=registry, retriever=retriever, checkpoint_store=checkpoint_store,
                       max_steps=max_steps, max_duration_seconds=budget)


@app.on_event("startup")
def start_consumer() -> None:
    if os.getenv("AUTO_CONSUME", "false") == "true":
        cp_url = _control_plane_url()
        runner = _build_runner()
        threading.Thread(target=consumer_loop, args=(runner, cp_url), daemon=True).start()


def _control_plane_url() -> str:
    return os.getenv("CONTROL_PLANE_URL", "http://control-plane:8080").rstrip("/")


def _submit_diagnosis(incident_id: int, diagnosis) -> None:
    evidence = [{"source": e.source, "key": e.key, "content": e.content} for e in diagnosis.evidence]
    tool_calls = [{
        "toolName": t.name,
        "argumentsJson": json.dumps(t.arguments, ensure_ascii=False),
        "status": t.status,
        "resultSummary": t.result_summary,
        "durationMs": t.duration_ms,
        "error": t.error,
        "createdAt": None,
    } for t in diagnosis.tool_calls]
    payload = {
        "rootCause": diagnosis.root_cause,
        "confidence": diagnosis.confidence,
        "evidence": evidence,
        "recommendedActions": diagnosis.recommended_actions,
        "toolCalls": tool_calls,
    }
    try:
        httpx.post(
            f"{_control_plane_url()}/api/v1/incidents/{incident_id}/diagnosis",
            json=payload,
            timeout=10,
            headers=agent_headers(),
        )
    except Exception:
        # Callback is best-effort; the caller still receives the diagnosis directly.
        pass


def _submit_verification(incident_id: int, verification) -> None:
    evidence = [{"source": e.source, "key": e.key, "content": e.content} for e in verification.evidence]
    payload = {
        "status": verification.status,
        "detail": verification.detail,
        "evidence": evidence,
    }
    try:
        httpx.post(
            f"{_control_plane_url()}/api/v1/incidents/{incident_id}/verification",
            json=payload,
            timeout=10,
            headers=agent_headers(),
        )
    except Exception:
        pass


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/agent/diagnose")
def diagnose(req: DiagnoseRequest) -> dict[str, Any]:
    runner = _build_runner()
    result = runner.run_diagnosis(req.incident_id, req.alert)
    threading.Thread(target=_submit_diagnosis, args=(req.incident_id, result.diagnosis), daemon=True).start()
    return {
        "incident_id": req.incident_id,
        "diagnosis": asdict(result.diagnosis),
        "state": result.state.to_dict(),
        "duration_ms": result.duration_ms,
        "resumed": result.resumed,
    }


@app.post("/api/v1/agent/verify")
def verify(req: VerifyRequest) -> dict[str, Any]:
    runner = _build_runner()
    # A real implementation would restore the checkpointed AgentState from DB.
    state = AgentState(incident_id=req.incident_id, alert=req.alert)
    result = runner.run_verification(state)
    if result.verification:
        _submit_verification(req.incident_id, result.verification)
    return {
        "incident_id": req.incident_id,
        "verification": asdict(result.verification) if result.verification else None,
        "state": result.state.to_dict(),
        "duration_ms": result.duration_ms,
    }
