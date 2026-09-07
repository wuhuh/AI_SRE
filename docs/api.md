# API Docs

核心 API 见 `docs/api-contract.md`。

主要调用关系（方向与 P1 后现状对齐——生产路径是 agent 轮询拉取，不是 CP 推送）：

```text
Alertmanager / Client
  → POST /api/v1/alerts/alertmanager（webhook secret）
  → Control Plane

Control Plane
  → outbox 建 agent_task 行（mq_status PENDING→SENT，RocketMQ 直连消费为
    EXPERIMENTAL 未接线——生产路径是轮询）

Agent Runtime（轮询拉取）
  → GET  /api/v1/tasks/pending（agent token）
  → POST /api/v1/tasks/{id}/claim（原子抢占）
  → Tool Server /api/k8s /api/redis /api/db（+ 直连 Prometheus/Loki/Tempo）
  → POST /api/v1/incidents/{id}/diagnosis /verification（agent token 回调）

Frontend
  → Control Plane /api/v1/incidents（JWT ≥VIEWER）
  → /api/v1/dashboard/*、/api/v1/approvals（决策需 ADMIN/OPERATOR）
```

生产建议为三个服务生成 OpenAPI。