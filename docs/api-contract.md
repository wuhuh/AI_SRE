# API Contract

## Control Plane -> Agent Runtime

`POST /api/v1/agent/diagnose`

```json
{
  "incident_id": 1,
  "alert": {
    "service": "payment-service",
    "alertName": "latency_high",
    "severity": "P1",
    "summary": "payment p99 high"
  }
}
```

Response:

```json
{
  "incident_id": 1,
  "diagnosis": {
    "root_cause": "redis_connection_pool_exhausted",
    "confidence": 0.91,
    "evidence": [],
    "recommended_actions": [],
    "tool_calls": []
  },
  "state": {},
  "duration_ms": 123
}
```

`POST /api/v1/agent/verify` uses the same alert envelope and returns verification status.

## Agent Runtime -> Control Plane

- Diagnosis result is written back through the shared database / task message.
- High-risk action creates an `Approval` via Control Plane REST API.

## Alertmanager Webhook

`POST /api/v1/alerts`

```json
{
  "service": "payment-service",
  "alertName": "latency_high",
  "resource": "payment-1",
  "severity": "P1",
  "summary": "payment p99 high",
  "labels": {"service": "payment-service"}
}
```

Response: `202 {"incidentId": 1, "duplicate": false}`

## REST API 汇总

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/alerts` | Alertmanager webhook ingestion |
| GET | `/api/v1/incidents` | Incident list |
| GET | `/api/v1/incidents/{id}` | Incident detail |
| POST | `/api/v1/incidents/{id}/transition` | Transition state machine |
| POST | `/api/v1/incidents/{id}/diagnosis` | Save Agent diagnosis result |
| POST | `/api/v1/incidents/{id}/verification` | Save Agent verification result |
| POST | `/api/v1/incidents/{id}/remediations` | Save remediation action |
| GET | `/api/v1/incidents/{id}/evidence` | List evidence |
| GET | `/api/v1/incidents/{id}/tool-calls` | List tool calls |
| GET | `/api/v1/incidents/{id}/steps` | List agent steps |
| GET | `/api/v1/incidents/{id}/remediations` | List remediation actions |
| GET | `/api/v1/incidents/{id}/audit-logs` | List audit logs |
| GET | `/api/v1/incidents/{id}/report` | Generate Incident Report |
| GET | `/api/v1/dashboard/summary` | Dashboard summary stats |
| POST | `/api/v1/approvals` | Create approval request |
| POST | `/api/v1/approvals/{id}/decision` | Approve/reject high-risk action |
| POST | `/api/v1/auth/login` | Login and get JWT |
| POST | `/mcp` | MCP-style JSON-RPC tool discovery/call |
| GET | `/api/v1/tasks/pending` | List pending agent tasks |
| POST | `/api/v1/tasks/{id}/complete` | Mark agent task complete |
| GET | `/api/v1/stream/incidents` | SSE stream for incident events |
| POST | `/api/v1/agent/diagnose` | Agent diagnosis (Agent Runtime) |
| POST | `/api/v1/agent/verify` | Recovery verification (Agent Runtime) |