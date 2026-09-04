# AI SRE Architecture

## System Architecture

```mermaid
flowchart LR
    A[Alertmanager / Webhook] --> CP[Control Plane Spring Boot]
    CP --> MQ[RocketMQ]
    MQ --> AR[Agent Runtime Python]
    AR --> TS[Tool Gateway]
    TS --> P[Prometheus]
    TS --> L[Loki]
    TS --> J[Jaeger/Tempo]
    TS --> K[Kubernetes API]
    TS --> R[Redis]
    TS --> D[PostgreSQL]
    AR --> KB[(Knowledge Base / pgvector)]
    CP --> PG[(PostgreSQL)]
    CP --> RD[(Redis)]
```

## Incident Sequence

```mermaid
sequenceDiagram
    participant A as Alertmanager
    participant CP as Control Plane
    participant MQ as RocketMQ
    participant AR as Agent Runtime
    participant TS as Tool Gateway
    participant O as Observability
    participant H as Human

    A->>CP: POST /api/v1/alerts
    CP->>CP: dedup + aggregate
    CP->>MQ: send diagnosis task
    MQ->>AR: consume task
    AR->>TS: query metrics/logs/traces
    TS->>O: query
    O-->>TS: data
    TS-->>AR: evidence
    AR-->>CP: structured RCA + action plan
    CP-->>H: approval request
    H-->>CP: approve
    CP->>TS: execute remediation
    AR->>TS: verify metrics/logs/traces
    AR-->>CP: verification result
    CP-->>A: incident resolved/report
```

## Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> PLANNING
    PLANNING --> DIAGNOSING
    DIAGNOSING --> ROOT_CAUSE_FOUND
    DIAGNOSING --> FAILED
    ROOT_CAUSE_FOUND --> WAITING_APPROVAL
    WAITING_APPROVAL --> REMEDIATING
    WAITING_APPROVAL --> REJECTED
    REMEDIATING --> VERIFYING
    VERIFYING --> RESOLVED
    VERIFYING --> DIAGNOSING
    RESOLVED --> [*]
    FAILED --> [*]
```

## Tool Permission Flow

```mermaid
flowchart LR
    A[Agent Action] --> P[Policy Engine]
    P -->|READ_ONLY| E[Execute]
    P -->|HIGH_RISK| W[WAITING_APPROVAL]
    W -->|approve| E
    W -->|reject| D[Denied]
```

## Database Schema

Core tables: `incident`, `alert`, `agent_task`, `agent_step`, `evidence`,
`tool_call`, `approval`, `remediation_action`, `audit_log`, `runbook`,
`evaluation_case`.

Indexes are designed for:
- alert dedup lookup: `alert(fingerprint, received_at)`
- incident list by status/service: `incident(status, started_at)`, `incident(service)`
- agent task query: `agent_task(incident_id)`, `agent_task(idempotency_key)`
- evidence/timeline query: `evidence(incident_id, collected_at)`
- audit/history query: `audit_log(incident_id, created_at)`

## API

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/alerts` | Alertmanager webhook ingestion |
| GET | `/api/v1/incidents` | Incident list |
| POST | `/api/v1/incidents/{id}/transition` | Transition state machine |
| POST | `/api/v1/approvals/{id}/decision` | Approve/reject high-risk action |
| POST | `/api/v1/agent/diagnose` | Agent diagnosis (Agent Runtime) |
| POST | `/api/v1/agent/verify` | Recovery verification (Agent Runtime) |