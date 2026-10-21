"""Background consumer for automatic diagnosis tasks.

In a production environment this would be a RocketMQ consumer. For local/demo
and environments where the RocketMQ Python client is not installed, this module
polls the Control Plane pending-task API. Both paths drive the same diagnosis
pipeline.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from typing import Any

from app.agent.runner import AgentRunner
from app.idempotency import FileIdempotencyStore
from app.masking import mask_sensitive


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


logger = logging.getLogger(__name__)


def agent_headers() -> dict:
    """P0-05: 控制面回调的共享 token（X-Agent-Token）；未配置时不带头（本地开发兼容）。"""
    token = os.getenv("AGENT_TOKEN", "").strip()
    return {"X-Agent-Token": token} if token else {}


def submit_diagnosis(cp_url: str, incident_id: int, diagnosis, task_id: int | None = None,
                     worker: str | None = None, claim_epoch: int | None = None) -> None:
    # P2-AR-09: 证据带溯源字段（timestamp 由 CP 落库时补）
    # 红线 39：工具结果/证据在入库前统一脱敏——此前 mask_sensitive 零调用，
    # 观测栈返回的 bearer token / api_key 会原样落进 incident_evidence 表。
    evidence = [{
        "source": e.source,
        "key": e.key,
        "content": mask_sensitive(e.content or ""),
        "query": getattr(e, "query", None),
        "timeRange": getattr(e, "time_range", None),
    } for e in diagnosis.evidence]
    tool_calls = [{
        "toolName": t.name,
        "argumentsJson": json.dumps(t.arguments, ensure_ascii=False),
        "status": t.status,
        "riskLevel": getattr(t, "risk_level", None) or "READ_ONLY",
        "resultSummary": mask_sensitive(t.result_summary or ""),
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
        # 文档 6.7 fencing：诊断回写必须携带现任持有者身份与认领世代，
        # 否则 CP 侧 fail-closed 拒绝（409）
        if worker is not None and claim_epoch is not None:
            payload["workerId"] = worker
            payload["claimEpoch"] = claim_epoch
    # P1-AR-05: submit 失败必须让调用方知道（重试 N 次后上抛）——
    # 否则诊断没落库任务却被 complete，事故永远停在诊断完成之前
    max_retries = int(os.getenv("SUBMIT_MAX_RETRIES", "3"))
    delay = float(os.getenv("SUBMIT_RETRY_DELAY_SECONDS", "0.5"))
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            _request_json("POST", f"{cp_url}/api/v1/incidents/{incident_id}/diagnosis", payload,
                          timeout=10, headers=agent_headers())
            return
        except Exception as exc:  # noqa: BLE001 - 重试边界
            last_exc = exc
            if attempt < max_retries:
                time.sleep(delay)
    raise RuntimeError(f"diagnosis submit failed after {max_retries + 1} attempts: {last_exc}")


def _worker_id() -> str:
    import socket
    return f"{socket.gethostname()}-{os.getpid()}"


class LeaseHeartbeat:
    """文档 6.5：诊断期间按固定周期续租（best-effort）。

    续租只能由现任持有者发起（worker + claimEpoch 与 fencing 同一条校验线）。
    409 = 任务已易主 / 租约失效 / 超总时长上限——此时停止心跳即可，
    本进程后续的回写无论如何都会被 CP 的 fencing 层拒绝，不会污染数据。
    """

    def __init__(self, cp_url: str, task_id: int, worker: str, claim_epoch: int | None,
                 interval_seconds: float):
        self._cp_url = cp_url
        self._task_id = task_id
        self._worker = worker
        self._claim_epoch = claim_epoch
        self._interval = max(interval_seconds, 1.0)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name=f"lease-hb-{self._task_id}")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                _request_json("POST", f"{self._cp_url}/api/v1/tasks/{self._task_id}/renew",
                              {"worker": self._worker, "claimEpoch": self._claim_epoch},
                              timeout=10, headers=agent_headers())
            except Exception as exc:  # noqa: BLE001 - 心跳失败不中断诊断
                logger.warning("lease renewal failed for task %s: %s "
                               "(results will be fenced if ownership was lost)",
                               self._task_id, exc)
                if "409" in str(exc):
                    return  # 已易主，继续心跳没有意义


def _lease_heartbeat_interval() -> float:
    # 默认 200s = 租约 600s 的 1/3；租约在 CP 侧配置（aisre.task.lease-seconds）
    return float(os.getenv("AGENT_LEASE_RENEW_SECONDS", "200"))


def consume_once(runner: AgentRunner, cp_url: str, idempotency_store=None) -> int:
    # P2-CP-23 补链：轮询也要带 agent token（P1-CP-14 读门控后无头轮询一直 401，
    # 且循环 except: pass 吞掉了错误 —— 现在至少 WARN 一行）
    tasks = _request_json("GET", f"{cp_url}/api/v1/tasks/pending", timeout=10,
                          headers=agent_headers()) or []
    processed = 0
    worker = _worker_id()
    from app.metrics import DIAGNOSES_TOTAL, DIAGNOSIS_DURATION, TASKS_PENDING
    # 红线 18：aisre_tasks_pending 此前全仓库从未 .set()，恒为 0——
    # Grafana「任务积压」面板是死的。轮询已经拿到了待认领清单，直接落这个数。
    TASKS_PENDING.set(len(tasks))
    for task in tasks:
        incident_id = task.get("incidentId")
        task_id = task.get("id")
        if incident_id is None:
            continue
        key = f"{task_id}:{task.get('type', 'DIAGNOSIS')}" if task_id else None
        if idempotency_store is not None and key and idempotency_store.is_processed(key):
            continue
        # P1-MQ-02: 先原子领取再诊断；抢不到说明任务已被其他副本处理，直接跳过
        claim_epoch = None
        if task_id is not None:
            try:
                claim = _request_json("POST", f"{cp_url}/api/v1/tasks/{task_id}/claim",
                                      {"worker": worker}, timeout=10, headers=agent_headers()) or {}
            except Exception:
                continue
            if not claim.get("claimed"):
                continue
            # 文档 6.7 fencing：本次认领的世代号，后续所有业务写入都要携带
            claim_epoch = (claim.get("task") or {}).get("claimEpoch")
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
            # 文档 6.5：诊断期间后台续租，防止长任务（重试/慢 LLM）被租约回收误判
            heartbeat = None
            if task_id is not None:
                heartbeat = LeaseHeartbeat(cp_url, task_id, worker, claim_epoch,
                                           _lease_heartbeat_interval())
                heartbeat.start()
            try:
                import time as _time
                _t0 = _time.monotonic()
                # 每次任务一个 checkpoint key：重诊（新 task/round）绝不能复用
                # 上一轮已完成的 diagnosis，否则自动重诊环会原地返回旧结论。
                result = runner.run_diagnosis(
                    incident_id, alert,
                    run_key=f"task-{task_id}" if task_id is not None else None)
                DIAGNOSIS_DURATION.observe(_time.monotonic() - _t0)
                DIAGNOSES_TOTAL.labels(status=result.diagnosis.status).inc()
                submit_diagnosis(cp_url, incident_id, result.diagnosis, task_id=task_id,
                                 worker=worker, claim_epoch=claim_epoch)
                if task_id is not None:
                    # 文档 6.7：终态写入带 worker + epoch，旧世代写不进终态
                    _request_json("POST", f"{cp_url}/api/v1/tasks/{task_id}/complete",
                                  {"worker": worker, "claimEpoch": claim_epoch},
                                  timeout=10, headers=agent_headers())
                if idempotency_store is not None and key:
                    idempotency_store.mark_processed(key)
                processed += 1
            finally:
                if heartbeat is not None:
                    heartbeat.stop()
        except Exception as exc:
            # P1-MQ-02: 失败上报终态，任务不再卡 RUNNING（租约回收兜底仍在）。
            # 409 = 任务已易主/已终态（fencing 拒绝）——这是正常竞争结果，不重试。
            if task_id is not None:
                try:
                    _request_json("POST", f"{cp_url}/api/v1/tasks/{task_id}/fail",
                                  {"error": str(exc)[:500], "worker": worker,
                                   "claimEpoch": claim_epoch},
                                  timeout=10, headers=agent_headers())
                except Exception:
                    pass
            continue
    return processed


def consumer_loop(runner: AgentRunner, cp_url: str, interval: float = 3.0, idempotency_store=None) -> None:
    store = idempotency_store or FileIdempotencyStore()
    while True:
        try:
            consume_once(runner, cp_url, store)
        except Exception as exc:
            logger.warning("consume_once failed: %s", exc)
        time.sleep(interval)
