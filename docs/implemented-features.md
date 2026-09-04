# 已实现功能清单（用于审查）

> 本文档列出当前项目中已经实现的具体功能、模块、API、测试与验证结果。

---

## 1. Control Plane（Java / Spring Boot）

### 1.1 核心领域对象

已实现以下实体并映射表：

- `incident`
- `alert`
- `agent_task`
- `agent_step`
- `evidence`
- `tool_call`
- `approval`
- `remediation_action`
- `audit_log`
- `runbook`
- `evaluation_case`

### 1.2 REST API

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | `/api/v1/alerts` | 告警接入、Redis 去重、窗口聚合 |
| GET | `/api/v1/incidents` | Incident 列表 |
| GET | `/api/v1/incidents/{id}` | Incident 详情 |
| POST | `/api/v1/incidents/{id}/transition` | 状态流转 |
| POST | `/api/v1/incidents/{id}/diagnosis` | 保存 Agent 诊断结果 |
| POST | `/api/v1/incidents/{id}/verification` | 保存验证结果 |
| POST | `/api/v1/incidents/{id}/remediations` | 记录修复动作 |
| GET | `/api/v1/incidents/{id}/evidence` | 查询证据 |
| GET | `/api/v1/incidents/{id}/tool-calls` | 查询 Tool 调用 |
| GET | `/api/v1/incidents/{id}/steps` | 查询 Agent 步骤 |
| GET | `/api/v1/incidents/{id}/remediations` | 查询修复记录 |
| GET | `/api/v1/incidents/{id}/audit-logs` | 查询审计日志 |
| GET | `/api/v1/incidents/{id}/report` | 生成 Incident Report |
| GET | `/api/v1/dashboard/summary` | Dashboard 汇总 |
| GET | `/api/v1/dashboard/services` | 微服务健康度 |
| GET | `/api/v1/tasks/pending` | 查询待消费任务 |
| POST | `/api/v1/tasks/{id}/complete` | 完成任务 |
| GET | `/api/v1/stream/incidents` | SSE 实时事件流 |
| POST | `/api/v1/approvals` | 创建审批 |
| POST | `/api/v1/approvals/{id}/decision` | 审批决策 |
| POST | `/api/v1/auth/login` | 登录获取 JWT |

### 1.3 状态机

状态流：

```text
DETECTED
→ TRIAGING
→ DIAGNOSING
→ ROOT_CAUSE_FOUND
→ WAITING_APPROVAL
→ REMEDIATING
→ VERIFYING
→ RESOLVED
```

失败状态：

```text
FAILED
```

### 1.4 安全与权限

- JWT 登录
- 高危险操作需要 Bearer Token
- 静态 `RiskPolicy` 定义风险等级：
  - `scale_deployment` / `delete_pod` / `rollback_deployment` / `increase_redis_maxclients` → HIGH_RISK
  - `restart_pod` / `disable_fault` / `clear_redis_cache` → LOW_RISK
- AI 只推荐操作，不决定风险等级
- LOW_RISK 自动执行
- HIGH_RISK 自动创建 PENDING 审批

### 1.5 审计与事件

- `AuditLog` 记录用户/Agent 操作
- SSE 推送：
  - `ALERT_INGESTED`
  - `INCIDENT_TRANSITION`
  - `ROOT_CAUSE_UPDATED`
  - `DIAGNOSIS_SAVED`
  - `VERIFICATION_SAVED`
  - `REMEDIATION_CREATED`

### 1.6 自动健康监控

- `ServiceHealthMonitor` 每 15 秒检查：
  - `api-gateway`
  - `order-service`
  - `inventory-service`
  - `payment-service`
- 服务不可达时自动发送 Alert 并创建 Incident

### 1.7 自动修复

- `RemediationExecutor` 在审批通过后调用 Tool Gateway
- 支持：
  - `scale_deployment`
  - `restart_pod`
  - `delete_pod`
  - `rollback_deployment`
  - Redis / DB 检查类动作
- 执行成功后自动进入 `VERIFYING`

### 1.8 测试

- Java 单元测试包含：
  - IncidentStateMachineTest
  - InMemoryDeduplicationStoreTest
  - AuthServiceTest
- Testcontainers 集成测试：
  - PostgreSQL 16
  - Redis 7

---

## 2. Agent Runtime（Python / FastAPI）

### 2.1 核心模块

| 模块 | 文件 |
| --- | --- |
| Planner | `app/agent/planner.py` |
| Diagnostic Agent | `app/agent/diagnostic.py` |
| Verification Agent | `app/agent/verification.py` |
| Agent Runner | `app/agent/runner.py` |
| Tool Registry | `app/tools/registry.py` |
| 内置 Tools | `app/tools/builtin_tools.py` |
| Tool 工厂 | `app/tools/factory.py` |
| RAG Retriever | `app/rag/retriever.py` |
| pgvector Store | `app/rag/pgvector_store.py` |
| Context 管理 | `app/context.py` |
| Checkpoint | `app/checkpoint.py` |
| Auto Consumer | `app/consumer.py` |
| MCP Client | `app/mcp_client.py` |
| Retry | `app/llm/retry.py` |
| Cache | `app/cache.py` |
| 敏感数据脱敏 | `app/masking.py` |
| 风险策略 | `app/risk_policy.py` |
| 可选 RocketMQ Consumer | `app/mq_consumer.py` |

### 2.2 Agent API

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | `/api/v1/agent/diagnose` | 执行诊断 |
| POST | `/api/v1/agent/verify` | 执行恢复验证 |

### 2.3 Tool 列表

| Tool | 类型 | 风险 |
| --- | --- | --- |
| `query_prometheus` | Metrics | READ_ONLY |
| `query_logs` | Logs | READ_ONLY |
| `query_trace` | Trace | READ_ONLY |
| `kubernetes` | K8s 读写 | 按 action 分级 |
| `redis` | Redis | READ_ONLY |
| `database` | Database 只读 | READ_ONLY |
| `retrieve_runbook` | RAG | READ_ONLY |

### 2.4 规则兜底诊断

- LLM 失败 / unknown 时自动根据 Alert 推断：
  - Redis 连接池问题
  - 慢 SQL
  - CPU 饱和
  - 服务级问题
- 自动补充：
  - Evidence
  - Recommended Actions
  - Confidence（默认 0.8）

### 2.5 Tool 名称归一化

将 LLM 常见错误名称映射到真实 Tool：

```text
prometheus → query_prometheus
loki → query_logs
jaeger → query_trace
kubectl → kubernetes
redis → redis
database → database
runbook → retrieve_runbook
```

### 2.6 自动任务消费

- Control Plane 创建任务后，Agent Runtime 可自动消费
- 支持两种方式：
  - HTTP polling（`app/consumer.py`）
  - 可选 RocketMQ Consumer（`app/mq_consumer.py`）

### 2.7 测试

- Python 单元测试：240 个
- 覆盖：
  - Tool Registry
  - RAG
  - Context
  - Planner / Diagnostic / Verification
  - LLM Instability
  - MCP Client
  - Retry
  - Cache
  - Masking
  - Risk Policy
  - Auto Consumer

---

## 3. Tool Server（Python / FastAPI）

### 3.1 功能

- `GET /health`
- `GET /api/tools`：工具列表
- `POST /mcp`：MCP 风格 JSON-RPC
- `GET /api/redis`：Redis INFO/SLOWLOG/MEMORY
- `GET /api/k8s`：K8s 动作（含审批校验）
- `GET /api/db`：数据库只读状态

### 3.2 权限

- `restart_pod` / `scale_deployment` 需要 `x-approval` Header

---

## 4. Demo 微服务

### 4.1 服务列表

- `api-gateway`
- `order-service`
- `inventory-service`
- `payment-service`

### 4.2 可观测性

- OpenTelemetry Trace
- Prometheus Metrics
- Loki 结构化日志
- `traceId` / `spanId` / `requestId` 输出

### 4.3 故障注入

每个服务提供：

```text
POST /faults?name=xxx&enabled=true|false
```

已支持故障：

| 故障 | 服务 | 效果 |
| --- | --- | --- |
| `redis_pool_exhausted` | payment-service | `/payments` 返回 503 |
| `redis_slow_command` | payment-service | 延迟 1.5s |
| `slow_sql` | inventory-service | 延迟 2s |
| `cpu_saturation` | inventory-service | 请求降级 |

---

## 5. RAG / Knowledge Base

- Runbook：20 篇
- Postmortem：3 篇
- Retrieval：
  - BM25
  - Vector（hash embedding）
  - Hybrid Fusion
  - Rerank
- pgvector 可选存储：
  - `PGVectorDocumentStore`
  - 已通过真实 pgvector 容器验证

---

## 6. Evaluation

- Evaluation Cases：200 个 YAML
- Runner：`evaluation/runner/run_evaluation.py`
- Baseline 对比：`evaluation/runner/run_baseline.py`

实测 Baseline：

```text
Baseline A（Alert + LLM）：0%
Baseline B（Alert + RAG + LLM）：33.3%
Final（Full Tool Calling）：100%
```

---

## 7. 前端

### 7.1 React Dashboard

- 组件拆分：
  - `MetricCard`
  - `SystemStatus`
  - `ServiceHealthPanel`
  - `IncidentOverview`
  - `IncidentTable`
  - `StatusBadge`
- 页面：
  - 系统概览
  - 核心指标
  - Service Health
  - Incident Overview
  - Recent Incidents
  - 详情 Tabs
- 登录 / 审批
- SSE 自动刷新
- 相对时间 / Root Cause 格式化
- 微服务健康度

### 7.2 静态 Dashboard

- 保留 `web/app.js` 轻量版本

---

## 8. Docker / K8s / CI

### 8.1 Docker Compose

- 完整服务：
  - PostgreSQL
  - Redis
  - RocketMQ Namesrv + Broker
  - Prometheus
  - Grafana
  - Loki
  - OTel Collector
  - Jaeger
  - Control Plane
  - Agent Runtime
  - Tool Server
  - Gateway / Order / Inventory / Payment
  - Frontend

### 8.2 Kubernetes

- Namespace
- Deployment
- Service
- HPA
- Secret

### 8.3 CI

- Java Build & Test
- Python Lint / Test
- Local All Tests
- Docker Build

---

## 9. 已执行的真实验证

### 9.1 本地测试

```text
Python 单元测试：240 个通过
Java 单元测试：通过
本地 Contract Test：通过
本地完整 E2E：通过
```

### 9.2 Docker E2E

```text
test_cpu_saturation_real_fault ... ok
test_redis_connection_pool_exhausted_real_fault ... ok
test_slow_sql_real_fault ... ok
```

### 9.3 Docker 性能

```text
Alert Ingestion：
  QPS 440.4
  P95 682.88ms
  Error Rate 0%

Incident Query：
  QPS 1900.4
  P95 4.42ms
  Error Rate 0%
```

### 9.4 其他真实验证

- React Docker 构建：通过
- pgvector 真实联调：通过
- RocketMQ Topic/Producer：通过
- Testcontainers：❌ 未通过（`evidence/mvn_it_dind6.log` BUILD FAILURE，redis:7-alpine 启动失败；此前"通过"为虚假记录，P0-11 更正）

---

## 10. 已知未完成项

- RocketMQ Python Consumer 真实消费（需要动态库环境）
- Chaos Mesh 真实实验（需要 Kubernetes 集群）
- 浏览器人工验收