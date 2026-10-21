from __future__ import annotations

import json
import logging
import os
import threading
import uuid

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
from app.masking import mask_sensitive
from app.models import AgentState
from app.rag.embeddings import OpenAICompatibleEmbeddingProvider
from app.rag.retriever import Document, HybridRetriever
from app.tools.factory import create_default_registry

app = FastAPI(title="AI SRE Agent Runtime", version="0.1.0")


class DiagnoseRequest(BaseModel):
    incident_id: int
    alert: dict[str, Any]
    # 可选：带任务 id 时复用该任务的 checkpoint（崩溃续跑）；
    # 不带时按每次请求生成唯一 manual key，避免手动重跑读到上一次结果。
    task_id: int | None = None
    # 开放诊断评测：prompt 不提供候选标签；生产默认 false，保持 CP 闭集契约。
    open_set: bool = False
    # 评测/压测默认不应把结果回写 CP（开放 label 会被闭集契约拒绝）。
    submit_result: bool = True


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


def _build_embedding_provider():
    """EMBEDDING_PROVIDER=openai 时启用真实 embedding；默认保持确定性本地向量。"""
    provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    if provider in ("openai", "openai-compatible"):
        return OpenAICompatibleEmbeddingProvider()
    return None


_RETRIEVER: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    """进程内复用 retriever：真实 embedding 下避免每个请求重新嵌入全部 runbook。"""
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = HybridRetriever(
            _load_runbook_docs(), embedding_provider=_build_embedding_provider())
    return _RETRIEVER


def _build_runner(open_set: bool = False) -> AgentRunner:
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
    retriever = _get_retriever()
    checkpoint_store = FileCheckpointStore() if os.getenv("CHECKPOINT_DIR") else None
    # P0-03: 诊断预算/步数可用环境变量调（默认与原行为一致）
    try:
        budget = float(os.getenv("DIAG_BUDGET_SECONDS", "15"))
        max_steps = int(os.getenv("DIAG_MAX_STEPS", "12"))
    except ValueError:
        budget, max_steps = 15.0, 12
    return AgentRunner(llm=llm, registry=registry, retriever=retriever, checkpoint_store=checkpoint_store,
                       max_steps=max_steps, max_duration_seconds=budget, open_set=open_set)


# P2-FI-08: 平台自监控（同端口挂载 /metrics，无需新开管理端口）
from prometheus_client import make_asgi_app

app.mount("/metrics", make_asgi_app())


def _consumer_worker_count() -> int:
    """有界并发：每个 worker 独立 runner，共享 CP 的原子 claim 防重复。"""
    try:
        configured = int(os.getenv("CONSUMER_WORKERS", "1"))
    except ValueError:
        configured = 1
    return max(1, min(configured, 16))


@app.on_event("startup")
def start_consumer() -> None:
    if os.getenv("AUTO_CONSUME", "false") == "true":
        cp_url = _control_plane_url()
        for index in range(_consumer_worker_count()):
            # 每个线程独立 runner：checkpoint key / tool cache 不跨任务竞争；
            # 任务是否重复执行由 CP 的 claim + fencing 决定。
            runner = _build_runner()
            threading.Thread(target=consumer_loop, args=(runner, cp_url),
                             daemon=True, name=f"agent-consumer-{index}").start()


def _control_plane_url() -> str:
    return os.getenv("CONTROL_PLANE_URL", "http://control-plane:8080").rstrip("/")


def _submit_diagnosis(incident_id: int, diagnosis) -> None:
    # 红线 39：同步路径同样先脱敏再出网（与 consumer.submit_diagnosis 对齐）
    evidence = [{"source": e.source, "key": e.key,
                 "content": mask_sensitive(e.content or "")} for e in diagnosis.evidence]
    tool_calls = [{
        "toolName": t.name,
        "argumentsJson": json.dumps(t.arguments, ensure_ascii=False),
        "status": t.status,
        # 红线 42：riskLevel 此前在同步路径漏发 → CP 侧缺省读作 READ_ONLY，
        # 高风险动作可能被当成只读而绕过审批。这里与 consumer 路径补齐同一字段。
        "riskLevel": getattr(t, "risk_level", None) or "READ_ONLY",
        "resultSummary": mask_sensitive(t.result_summary or ""),
        "durationMs": t.duration_ms,
        "error": mask_sensitive(t.error) if t.error else t.error,
        "createdAt": None,
    } for t in diagnosis.tool_calls]
    payload = {
        "rootCause": diagnosis.root_cause,
        "confidence": diagnosis.confidence,
        # 与 consumer 路径保持同一契约：状态/原因/候选/降级/token 全部透出。
        "status": diagnosis.status,
        "reasonCode": diagnosis.reason_code,
        "candidateRootCauses": diagnosis.candidate_root_causes,
        "fallbackUsed": diagnosis.fallback_used,
        "llmInputTokens": diagnosis.llm_input_tokens,
        "llmOutputTokens": diagnosis.llm_output_tokens,
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
    # P2-AR-09: 证据带溯源字段；P2-CP-23: taskId 链路关联
    evidence = [{
        "source": e.source,
        "key": e.key,
        # 验证路径与诊断路径同一脱敏边界：证据出网前必须 mask。
        "content": mask_sensitive(e.content or ""),
        "query": getattr(e, "query", None),
        "timeRange": getattr(e, "time_range", None),
    } for e in verification.evidence]
    payload = {
        "status": verification.status,
        "detail": mask_sensitive(verification.detail or ""),
        "evidence": evidence,
        "taskId": getattr(verification, "task_id", None),
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
    runner = _build_runner(open_set=req.open_set)
    run_key = (f"task-{req.task_id}" if req.task_id is not None
               else f"manual-{uuid.uuid4().hex}")
    result = runner.run_diagnosis(req.incident_id, req.alert, run_key=run_key)
    if req.submit_result:
        threading.Thread(target=_submit_diagnosis, args=(req.incident_id, result.diagnosis),
                         daemon=True).start()
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
