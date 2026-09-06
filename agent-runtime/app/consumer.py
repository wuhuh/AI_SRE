"""Background consumer for automatic diagnosis tasks.

In a production environment this would be a RocketMQ consumer. For local/demo
and environments where the RocketMQ Python client is not installed, this module
polls the Control Plane pending-task API. Both paths drive the same diagnosis
pipeline.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any

from app.agent.runner import AgentRunner
from app.idempotency import FileIdempotencyStore


def _request_json(method: str, url: str, payload: dict | None = None, timeout: float = 10,
                  headers: dict | None = None) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers = {"Content-Type": "application/json"} if data else {}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else None


def agent_headers() -> dict:
    """P0-05: 控制面回调的共享 token（X-Agent-Token）；未配置时不带头（本地开发兼容）。"""
    token = os.getenv("AGENT_TOKEN", "").strip()
    return {"X-Agent-Token": token} if token else {}


def submit_diagnosis(cp_url: str, incident_id: int, diagnosis, task_id: int | None = None) -> None:
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
    if task_id is not None:
        payload["taskId"] = task_id
    try:
        _request_json("POST", f"{cp_url}/api/v1/incidents/{incident_id}/diagnosis", payload,
                      timeout=10, headers=agent_headers())
    except Exception:
        pass


def _worker_id() -> str:
    import socket
    return f"{socket.gethostname()}-{os.getpid()}"


def consume_once(runner: AgentRunner, cp_url: str, idempotency_store=None) -> int:
    tasks = _request_json("GET", f"{cp_url}/api/v1/tasks/pending", timeout=10) or []
    processed = 0
    worker = _worker_id()
    for task in tasks:
        incident_id = task.get("incidentId")
        task_id = task.get("id")
        if incident_id is None:
            continue
        key = f"{task_id}:{task.get('type', 'DIAGNOSIS')}" if task_id else None
        if idempotency_store is not None and key and idempotency_store.is_processed(key):
            continue
        # P1-MQ-02: 先原子领取再诊断；抢不到说明任务已被其他副本处理，直接跳过
        if task_id is not None:
            try:
                claim = _request_json("POST", f"{cp_url}/api/v1/tasks/{task_id}/claim",
                                      {"worker": worker}, timeout=10, headers=agent_headers()) or {}
            except Exception:
                continue
            if not claim.get("claimed"):
                continue
        try:
            # P1-CP-14: 控制面读接口需要凭据（agent token 或 JWT）
            incident = _request_json("GET", f"{cp_url}/api/v1/incidents/{incident_id}",
                                     timeout=10, headers=agent_headers()) or {}
            alert = {
                "service": incident.get("service", "unknown"),
                "alertName": "auto-consumed",
                "severity": incident.get("severity", "P1"),
                "summary": incident.get("summary", ""),
            }
            result = runner.run_diagnosis(incident_id, alert)
            submit_diagnosis(cp_url, incident_id, result.diagnosis, task_id=task_id)
            if task_id is not None:
                _request_json("POST", f"{cp_url}/api/v1/tasks/{task_id}/complete", {},
                              timeout=10, headers=agent_headers())
            if idempotency_store is not None and key:
                idempotency_store.mark_processed(key)
            processed += 1
        except Exception as exc:
            # P1-MQ-02: 失败上报终态，任务不再卡 RUNNING（租约回收兜底仍在）
            if task_id is not None:
                try:
                    _request_json("POST", f"{cp_url}/api/v1/tasks/{task_id}/fail",
                                  {"error": str(exc)[:500]}, timeout=10, headers=agent_headers())
                except Exception:
                    pass
            continue
    return processed


def consumer_loop(runner: AgentRunner, cp_url: str, interval: float = 3.0, idempotency_store=None) -> None:
    store = idempotency_store or FileIdempotencyStore()
    while True:
        try:
            consume_once(runner, cp_url, store)
        except Exception:
            pass
        time.sleep(interval)
