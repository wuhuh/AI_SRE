# API Docs

核心 API 见 `docs/api-contract.md`。

主要调用关系：

```text
Alertmanager / Client
  → POST /api/v1/alerts
  → Control Plane

Control Plane
  → RocketMQ task
  → Agent Runtime /api/v1/agent/diagnose

Agent Runtime
  → Tool Server /mcp /api/k8s /api/redis /api/db
  → Control Plane /api/v1/incidents/{id}/diagnosis

Frontend
  → Control Plane /api/v1/incidents
  → /api/v1/dashboard/*
  → /api/v1/approvals
```

生产建议为三个服务生成 OpenAPI。