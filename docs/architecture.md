# AI SRE Architecture

> 与代码对齐版（2026-09）。生产路径 = 控制面轮询消费；RocketMQ 直连消费为
> EXPERIMENTAL（见 docs/security.md 与 agent-runtime/app/mq_consumer.py）。

## System Architecture

```mermaid
flowchart LR
    A[Alertmanager] -->|webhook + X-Webhook-Token| CP[Control Plane Spring Boot]
    CP -->|outbox: agent_task 行 + mq_status| MQ[(RocketMQ)]
    CP -->|GET /tasks/pending 轮询<br/>+ claim/complete/fail| AR[Agent Runtime Python]
    AR -->|X-Agent-Token| CP
    AR --> TS[Tool Gateway]
    TS --> P[Prometheus]
    TS --> L[Loki]
    TS --> J[Tempo]
    TS --> K[Kubernetes API]
    TS --> R[(Redis)]
    CP --> PG[(PostgreSQL)]
    CP --> R
    F[React Frontend] -->|Bearer JWT| CP
```

说明：
- MQ 消息由 CP outbox 产生（事务 afterCommit 发送 + 扫描器补发，P1-CP-07），
  但 agent-runtime 的 MQ 消费端**未接线**；任务分发的生产路径是轮询
  `GET /api/v1/tasks/pending` + 原子 `claim`（P1-MQ-01 方案 a）。
- 修复执行（HTTP 外呼 tool-server）在事务 afterCommit + REQUIRES_NEW 中运行（P1-CP-11）。

## Incident Sequence

```mermaid
sequenceDiagram
    participant A as Alertmanager
    participant CP as Control Plane
    participant AR as Agent Runtime
    participant TS as Tool Gateway
    participant O as Observability
    participant H as Human

    A->>CP: POST /api/v1/alerts/alertmanager (webhook secret)
    CP->>CP: dedup(指纹+首见计数) + 聚合 + 建 incident
    CP->>CP: outbox 建任务行（mq_status=PENDING→SENT）
    loop 轮询（AUTO_CONSUME）
        AR->>CP: GET /tasks/pending → POST claim（条件更新抢占）
    end
    AR->>CP: GET /incidents/{id}（agent token）
    AR->>TS: 查指标/日志/trace（spec.timeout_seconds 强制）
    TS->>O: query
    O-->>AR: evidence
    AR->>CP: POST /incidents/{id}/diagnosis（重试 N 次后上抛）
    Note over CP: 高风险动作 → WAITING_APPROVAL（审批 TTL 1h）
    CP-->>H: 审批单
    H->>CP: POST /approvals/{id}/decision（JWT ADMIN/OPERATOR）
    alt APPROVE
        CP->>TS: 执行修复（afterCommit + REQUIRES_NEW）
    else REJECT
        CP->>CP: WAITING_APPROVAL → ROOT_CAUSE_FOUND（可重新诊断）
    end
    Note over AR: 观察窗（默认 60s）后确定性 SLI 判定<br/>error_rate/p95 阈值 → RECOVERED|NOT_RECOVERED|UNKNOWN
    AR->>CP: POST /incidents/{id}/verification（LLM 仅写解释）
    CP->>CP: VERIFYING → RESOLVED（审计 + 事件）
```

## Incident State Machine（与 IncidentStateMachine.java 对齐）

```mermaid
stateDiagram-v2
    [*] --> DETECTED
    DETECTED --> TRIAGING
    TRIAGING --> DIAGNOSING
    DIAGNOSING --> ROOT_CAUSE_FOUND
    ROOT_CAUSE_FOUND --> WAITING_APPROVAL
    ROOT_CAUSE_FOUND --> VERIFYING
    WAITING_APPROVAL --> REMEDIATING
    WAITING_APPROVAL --> ROOT_CAUSE_FOUND
    REMEDIATING --> VERIFYING
    VERIFYING --> RESOLVED
    VERIFYING --> DIAGNOSING
    FAILED --> TRIAGING
```

非法流转抛 409（P1-CP-10）；并发更新由 Incident `@Version` 乐观锁保护（冲突同样 409）。

## Agent Task 生命周期（P1-MQ-02/03）

```text
QUEUED --claim(条件更新)--> RUNNING --complete--> COMPLETED
                                  |--fail------> FAILED
RUNNING(租约超时) --回收--> attempts+1: 未达上限 → QUEUED；达上限 → DEAD（毒任务，DLQ 等价物）
```

## Tool Permission Flow

```mermaid
flowchart LR
    A[Agent Action] --> P[RiskPolicy]
    P -->|READ_ONLY / LOW_RISK| E[Execute + auto-policy 审批]
    P -->|HIGH_RISK| W[WAITING_APPROVAL 人工审批]
    W -->|APPROVE| E
    W -->|REJECT| D[回 ROOT_CAUSE_FOUND]
```

## Database Schema

Flyway 单轨（V1..V7，`ddl-auto=validate`，P1-CP-17）。核心表：`incident`（@Version）、
`alert`、`agent_task`（idempotency_key 唯一、mq_status/mq_attempts、attempts/claim 租约）、
`agent_step`、`evidence`、`tool_call`、`approval`（expires_at、execution_token）、
`remediation_action`、`audit_log`、`runbook`、`evaluation_case`。

## API（主要端点）

| Method | Path | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/v1/alerts/alertmanager` | X-Webhook-Token | 告警接入（未配置 secret 时放行+WARN） |
| GET | `/api/v1/incidents` | JWT ≥VIEWER 或 agent token | 事故列表 |
| POST | `/api/v1/incidents/{id}/diagnosis` | X-Agent-Token | 诊断回调 |
| POST | `/api/v1/incidents/{id}/verification` | X-Agent-Token | 验证回调 |
| POST | `/api/v1/incidents/{id}/transition` | JWT ADMIN/OPERATOR | 状态推进（非法→409） |
| POST | `/api/v1/approvals/{id}/decision` | JWT ADMIN/OPERATOR | 审批（过期/已决→409） |
| GET/POST | `/api/v1/tasks/*` | 读=JWT/agent token；claim/complete/fail=agent token | 任务生命周期 |
| GET | `/api/v1/stream` | 公开（EventSource 无法带头） | SSE 事件流 |
| POST | `/api/v1/auth/login` | 公开 | 登录（BCrypt，strict 模式禁默认口令） |

管理端点（metrics/prometheus）在独立端口 8085（P1-CP-14）。
