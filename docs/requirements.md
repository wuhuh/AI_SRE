# 项目开发总 Prompt：AI SRE 智能故障诊断与自愈平台

你现在是一名 **Staff/Principal 级 AI Infra + 分布式后端工程师**，需要从零设计并实现一个可以真实运行、测试、压测、演示的完整生产级项目。

项目名称暂定：

**AI SRE — 基于 Multi-Agent、RAG、MCP 与 OpenTelemetry 的智能故障诊断与自愈平台**

你的任务不是写一个 Demo，而是完成一个具有较完整工程体系的项目，包括：

- 系统设计
- 后端服务
- Agent Runtime
- RAG
- MCP/Tool Calling
- Metrics / Logs / Traces
- Kubernetes
- Redis
- RocketMQ
- PostgreSQL
- 故障注入
- 权限控制
- Human-in-the-loop
- 测试
- Evaluation
- Benchmark
- CI/CD
- Docker Compose
- Kubernetes 部署
- 完整文档

最终项目必须能够从一次真实告警开始，自动完成：

**告警接入 → 去重聚合 → 故障任务创建 → Metrics/Logs/Traces 查询 → Agent 推理 → Runbook 检索 → Root Cause 定位 → 修复方案生成 → 高风险操作人工审批 → Tool 执行 → 故障恢复验证 → Incident Report 生成。**

------

# 一、总体开发原则

必须遵守以下原则。

## 1. 不允许只做 Demo

不能只实现：

```text
用户输入故障
→ 调用 LLM
→ 输出一段诊断文字
```

Agent 的每一个结论必须尽量来自真实系统数据，例如：

- Prometheus Metrics
- Loki Logs
- OpenTelemetry Trace
- Kubernetes API
- Redis INFO
- MySQL/PostgreSQL
- RocketMQ
- Runbook Knowledge Base

必须存在真正的 Tool Calling。

------

## 2. 核心逻辑不能完全依赖 Agent 框架黑盒

允许使用：

- LangGraph
- LangChain
- OpenAI SDK
- MCP SDK

但是以下核心能力必须能够清楚解释：

- Agent State
- Task State Machine
- Tool Registry
- Tool Permission
- Retry
- Timeout
- Checkpoint
- Context Management
- Evidence 管理
- Human Approval

不要让整个项目变成：

```python
agent = create_agent(...)
agent.run()
```

需要把核心机制显式设计出来。

------

# 二、推荐技术栈

尽量采用以下技术栈。

## 后端 Control Plane

Java：

```text
Java 21
Spring Boot 3.x
Spring WebFlux 或 Spring MVC
MyBatis / MyBatis-Plus 或 Spring Data JPA
PostgreSQL
Redis
RocketMQ
Resilience4j
OpenTelemetry
JUnit 5
Testcontainers
```

后端负责：

- Incident 管理
- Alert 接入
- Task 管理
- MQ
- 权限
- 审批
- Audit Log
- SSE/WebSocket
- API
- Agent Job 生命周期
- Dashboard 数据

------

## Agent Runtime

Python：

```text
Python 3.11+
FastAPI
Pydantic
OpenAI-compatible SDK
LangGraph（可选）
MCP SDK
pytest
```

负责：

- Planner
- Diagnostic Agent
- Verification Agent
- RAG
- Tool Calling
- Context 管理
- Evidence 管理
- Diagnosis
- Action Plan
- Incident Summary

必须抽象：

```text
LLMProvider

Tool

ToolRegistry

AgentState

AgentRunner

Retriever

MemoryStore

CheckpointStore
```

不能与某一家模型 API 强绑定。

------

# 三、整体系统架构

目标架构：

```text
                         ┌────────────────┐
                         │ Grafana / Web  │
                         └────────┬───────┘
                                  │
                            REST / SSE
                                  │
                    ┌─────────────▼────────────┐
                    │     Control Plane        │
                    │      Spring Boot         │
                    │                          │
                    │ Alert Management         │
                    │ Incident Management      │
                    │ Task State Machine       │
                    │ Approval                 │
                    │ RBAC                     │
                    │ Audit                    │
                    └─────────────┬────────────┘
                                  │
                              RocketMQ
                                  │
                     ┌────────────▼────────────┐
                     │     Agent Runtime       │
                     │        Python           │
                     │                         │
                     │ Planner                 │
                     │ Diagnostic Agent        │
                     │ Verification Agent      │
                     │ Context Manager         │
                     │ Evidence Store          │
                     └───────┬─────────┬───────┘
                             │         │
                        RAG  │         │ MCP
                             │         │
             ┌───────────────▼─┐   ┌───▼───────────────┐
             │ Knowledge Base  │   │ Tool Gateway      │
             │ pgvector/BM25   │   │                  │
             │ Runbook         │   │ Prometheus       │
             │ Postmortem      │   │ Loki             │
             └─────────────────┘   │ Trace            │
                                   │ Kubernetes       │
                                   │ Redis            │
                                   │ Database         │
                                   └───────┬──────────┘
                                           │
                                  Demo Microservices
```

------

# 四、必须搭建故障实验环境

自己搭建一个小型微服务系统作为诊断对象。

至少包含：

```text
api-gateway
order-service
inventory-service
payment-service
```

依赖：

```text
PostgreSQL/MySQL
Redis
RocketMQ
```

调用关系示例：

```text
Client
  ↓
API Gateway
  ↓
Order Service
  ├── Inventory Service
  └── Payment Service
          ↓
        Redis
```

所有服务必须接入 OpenTelemetry。

必须能够观察：

```text
HTTP Request
→ Gateway
→ Order
→ Payment
→ Redis
```

的完整 Trace。

------

# 五、Observability 系统

必须完成三类 Observability 数据。

## Metrics

使用：

```text
Prometheus
Grafana
```

至少收集：

```text
QPS

HTTP latency
P50
P95
P99

5xx rate

CPU

Memory

JVM Heap

GC

Thread Pool

Database Connection Pool

Redis Latency

Redis Connection Pool

RocketMQ Consumer Lag
```

------

## Logs

优先使用：

```text
Loki
```

所有日志至少包含：

```text
timestamp
service
level
traceId
spanId
requestId
message
```

必须支持 Agent 按：

```text
service
time range
traceId
keyword
```

查询日志。

------

## Trace

使用：

```text
OpenTelemetry
+
Jaeger 或 Tempo
```

Agent 必须可以查询：

```text
Trace
Span
Duration
Error Span
Service Dependency
```

------

# 六、Incident 流程

设计完整 Incident 生命周期。

例如：

```text
DETECTED
↓
TRIAGING
↓
DIAGNOSING
↓
ROOT_CAUSE_FOUND
↓
WAITING_APPROVAL
↓
REMEDIATING
↓
VERIFYING
↓
RESOLVED
```

失败：

```text
FAILED
```

Agent 执行必须持久化状态。

数据库至少设计：

```text
incident

alert

agent_task

agent_step

evidence

tool_call

approval

remediation_action

audit_log

runbook

evaluation_case
```

需要设计索引，并解释为什么这样设计。

------

# 七、Alert 接入

实现：

```text
POST /api/v1/alerts
```

支持类似 Alertmanager Webhook。

需要完成：

## 去重

例如：

```text
fingerprint =
service
+
alertName
+
resource
```

------

## 聚合

同一时间窗口内：

```text
payment latency high
payment 5xx high
redis connection high
```

可以归为同一 Incident。

------

## 防止告警风暴

使用：

```text
Redis
+
TTL
+
Debounce
```

需要测试大量重复告警。

------

# 八、Agent 设计

不要一开始做十几个 Agent。

第一版设计三个核心角色即可。

## Planner

负责：

```text
分析 Alert

决定需要查询哪些信息

制定诊断计划
```

例如：

```text
1. Query payment-service metrics
2. Query Redis metrics
3. Search related logs
4. Query slow traces
5. Retrieve Runbook
```

------

## Diagnostic Agent

通过循环：

```text
Plan
↓
Tool Call
↓
Observation
↓
Evidence
↓
Reason
↓
Next Tool
```

最终输出结构化结果：

```json
{
  "rootCause": "",
  "confidence": 0.0,
  "evidence": [],
  "recommendedActions": []
}
```

不要仅输出自然语言。

------

## Verification Agent

执行 remediation 后再次检查：

```text
Metrics
Logs
Trace
```

判断：

```text
RECOVERED

NOT_RECOVERED

UNKNOWN
```

如果未恢复，不允许直接把 Incident 标记为 RESOLVED。

------

# 九、Evidence 系统

这是整个系统非常重要的设计。

Agent 的结论必须有 Evidence。

例如：

```text
E1:
payment-service P99 = 3.2s

E2:
95% slow traces caused by Redis span

E3:
Redis active connections = max

E4:
logs contain Pool exhausted
```

最终：

```text
Root Cause:
Redis connection pool exhausted

Confidence:
0.91

Evidence:
E1 + E2 + E3 + E4
```

Evidence 需要持久化。

避免：

```text
LLM:
“我认为可能是 Redis”
```

但无法证明。

------

# 十、Tool / MCP 系统

至少实现这些 Tool：

## Prometheus

```text
query_metric
query_range
```

------

## Log

```text
query_logs
```

------

## Trace

```text
query_trace
get_slow_traces
```

------

## Kubernetes

Read：

```text
list_pods
get_pod
get_deployment
get_events
get_pod_logs
```

Write：

```text
restart_pod
scale_deployment
```

------

## Redis

```text
redis_info
redis_slowlog
redis_memory
```

------

## Database

只读：

```text
db_health
db_active_connections
db_slow_query
explain_query
```

第一阶段禁止 Agent 任意执行 SQL。

------

# 十一、Tool 安全系统

Tool 分类：

```text
READ_ONLY

LOW_RISK

HIGH_RISK
```

例如：

```text
query_prometheus
READ_ONLY

restart_pod
LOW/HIGH_RISK

scale_deployment
HIGH_RISK
```

HIGH_RISK 必须：

```text
Agent Action
↓
Policy Engine
↓
WAITING_APPROVAL
↓
Human Approve
↓
Execute
```

实现：

```text
RBAC
Tool Whitelist
Parameter Validation
Timeout
Audit Log
Rate Limit
```

禁止：

```text
Agent 自由执行任意 shell
Agent 自由执行 kubectl
Agent 自由执行 SQL DELETE
```

------

# 十二、RAG Knowledge Base

Knowledge Base 至少包含：

```text
Runbook

Postmortem

Troubleshooting Guide

System Architecture

Service Dependency
```

至少自己编写：

```text
20+ Runbook
```

------

## Retrieval Pipeline

实现：

```text
Query Rewrite

↓
BM25

+
Embedding Retrieval

↓
Fusion

↓
Rerank

↓
Top-K
```

第一版可以：

```text
PostgreSQL
+
pgvector
```

避免引入过多中间件。

需要比较：

```text
Vector Only

BM25 Only

Hybrid
```

在故障检索上的效果。

------

# 十三、Context Management

不要无限累积 Agent History。

实现：

```text
Recent Steps

Critical Evidence

Incident Summary

Tool Result Summary

Retrieved Knowledge
```

Tool Result 如果过长：

```text
原始结果持久化

上下文仅保留摘要 + reference
```

需要避免：

```text
几十 KB 日志全部塞给 LLM
```

可以设计：

```text
Context Budget
```

并记录：

```text
input tokens
output tokens
total tool calls
```

------

# 十四、故障注入

必须自己构建真实故障。

至少实现以下 10 类：

## Case 1

```text
Redis connection pool exhausted
```

## Case 2

```text
Database connection pool exhausted
```

## Case 3

```text
Slow SQL
```

## Case 4

```text
CPU saturation
```

## Case 5

```text
Memory leak / high memory
```

## Case 6

```text
Downstream HTTP timeout
```

## Case 7

```text
Pod CrashLoopBackOff
```

## Case 8

```text
RocketMQ message backlog
```

## Case 9

```text
Thread Pool exhausted
```

## Case 10

```text
Redis slow command / latency
```

优先通过：

```text
故障注入脚本
Chaos Mesh
Stress 工具
配置修改
```

实现。

每个 Fault Case 必须包含：

```text
fault description
fault injection
expected symptoms
expected root cause
expected evidence
recovery operation
verification method
```

------

# 十五、Evaluation Dataset

建立：

```text
evaluation/
    cases/
```

例如：

```yaml
id: redis_pool_001

fault_type: redis_connection_pool_exhausted

service: payment-service

expected_root_cause:
  redis_connection_pool_exhausted

expected_evidence:
  - redis_connection_usage_high
  - redis_timeout_log
  - redis_span_latency_high
```

第一阶段至少：

```text
30 Case
```

最终目标：

```text
50~100 Case
```

不要为了数量大量复制相同 Case。

------

# 十六、Evaluation 指标

实现自动 Evaluation Runner。

至少计算：

```text
Root Cause Top-1 Accuracy

Root Cause Top-3 Accuracy

Diagnosis Success Rate

Tool Success Rate

Average Tool Calls

Average Diagnosis Time

P95 Diagnosis Time

Average Input Tokens

Average Output Tokens

Human Approval Rate

Recovery Success Rate
```

如果可以，再增加：

```text
Evidence Precision

Evidence Recall
```

------

# 十七、Baseline

必须有 Baseline。

至少比较：

## Baseline A

```text
仅 Alert
+
LLM
```

## Baseline B

```text
Alert
+
RAG
+
LLM
```

## Final

```text
Alert
+
Metrics
+
Logs
+
Trace
+
RAG
+
Agent Tool Calling
```

通过实验说明：

```text
加入 Tool 和 Evidence 后
RCA 是否提升
```

不要虚构结果。

所有指标必须来自真实运行。

------

# 十八、测试体系

必须实现完整测试。

## Unit Test

覆盖：

```text
Alert Dedup

Incident State Machine

Permission Policy

Tool Validation

Context Builder

RAG Fusion

Agent Result Parser
```

------

## Integration Test

使用：

```text
Testcontainers
```

测试：

```text
PostgreSQL
Redis
RocketMQ
```

------

## Contract Test

确保：

```text
Java Control Plane
↔
Python Agent Runtime
```

接口一致。

------

## Agent Tool Test

每个 Tool：

```text
Success
Timeout
Invalid Argument
Backend Failure
Unauthorized
```

都要测试。

------

## E2E Test

至少实现：

```text
故障注入
↓
触发告警
↓
Incident
↓
Agent
↓
Diagnosis
↓
Approval
↓
Remediation
↓
Verification
```

完整测试。

------

# 十九、LLM 不稳定性测试

测试：

```text
LLM timeout

LLM 429

Invalid JSON

Hallucinated Tool

Unknown Tool

Tool argument invalid

Agent infinite loop
```

实现：

```text
Retry

Timeout

Max Steps

Structured Output Validation

Fallback

Graceful Failure
```

------

# 二十、异常恢复

测试：

```text
Agent Runtime Crash

Control Plane Restart

RocketMQ 重复消费

Tool 请求超时

数据库短暂不可用
```

要求：

```text
任务不能无故丢失
```

至少实现：

```text
Persistent Task State

Idempotency Key

Retry

Checkpoint

Duplicate Detection
```

------

# 二十一、并发与性能测试

使用：

```text
k6
```

测试 API：

```text
Alert ingestion

Incident query

SSE stream
```

例如：

```text
10
50
100
300
500
```

并发逐级测试。

记录：

```text
QPS

P50

P95

P99

Error Rate
```

不要预先编造性能指标。

------

# 二十二、Agent Benchmark

同时测试：

```text
1
5
10
20
```

个并行 Incident。

观察：

```text
LLM concurrency

Tool concurrency

DB connection

Redis

RocketMQ backlog

CPU

Memory
```

分析瓶颈。

------

# 二十三、Cache

可以加入：

```text
Metrics Query Cache

Runbook Retrieval Cache

Tool Result Short TTL Cache
```

但必须考虑：

```text
stale data
```

例如 Metrics Cache TTL 必须非常短。

测试缓存前后：

```text
Latency

Backend Query Count
```

------

# 二十四、前端

前端不需要非常复杂。

可以：

```text
React
+
Ant Design
```

至少展示：

## Incident List

```text
severity
service
status
start time
root cause
```

## Incident Detail

展示：

```text
Alert

Timeline

Agent Step

Tool Call

Evidence

Root Cause

Remediation

Approval

Verification
```

最重要的是：

**Agent Diagnosis Timeline**

例如：

```text
21:01 Alert received

21:01 Query Prometheus

21:02 Redis latency anomaly found

21:02 Query Trace

21:03 Redis spans dominate latency

21:03 Query Logs

21:03 ConnectionPoolTimeout detected

21:04 Root Cause identified
```

这样非常适合现场 Demo。

------

# 二十五、Security

至少完成：

```text
JWT Authentication

RBAC

Tool Permission

Audit Log

Secret via environment

Sensitive Data Masking
```

禁止：

```text
API Key
Password
Token
```

提交到 Git。

------

# 二十六、Docker Compose

最终必须：

```bash
docker compose up -d
```

能够启动核心环境。

包括：

```text
PostgreSQL
Redis
RocketMQ
Prometheus
Grafana
Loki
OTel Collector
Jaeger/Tempo
Control Plane
Agent Runtime
Demo Services
```

如果资源压力太大，可以提供：

```text
docker-compose-lite.yml
docker-compose-full.yml
```

------

# 二十七、Kubernetes

Docker Compose 完成后再做 Kubernetes。

使用：

```text
kind
```

或：

```text
minikube
```

部署：

```text
Demo services
Control plane
Agent runtime
```

增加：

```text
Deployment
Service
ConfigMap
Secret
HPA
```

不要一开始就直接做 Kubernetes，先保证 Compose 跑通。

------

# 二十八、CI

GitHub Actions 至少包含：

```text
Java Build

Python Lint

Unit Tests

Integration Tests

Docker Build
```

PR 必须能够执行基础测试。

------

# 二十九、代码质量

要求：

```text
禁止核心代码留下 TODO

禁止 catch(Exception) 后直接忽略

禁止 hardcode secret

禁止测试依赖真实在线 LLM

LLM Test 使用 Mock Provider
```

代码结构必须有清晰边界。

------

# 三十、项目目录建议

```text
ai-sre/
│
├── control-plane/
│
├── agent-runtime/
│
├── tool-server/
│
├── demo-services/
│   ├── gateway/
│   ├── order-service/
│   ├── inventory-service/
│   └── payment-service/
│
├── knowledge-base/
│   ├── runbooks/
│   └── postmortems/
│
├── evaluation/
│   ├── cases/
│   └── runner/
│
├── fault-injection/
│
├── observability/
│
├── deploy/
│   ├── docker/
│   └── k8s/
│
├── benchmark/
│
├── docs/
│
└── README.md
```

------

# 三十一、开发阶段

必须严格按阶段实施。

不要一次性生成整个项目。

## Phase 0：Architecture

首先输出：

```text
requirements.md

architecture.md

模块划分

数据流

数据库 Schema

API

技术选型

风险
```

然后检查架构是否过度设计。

------

## Phase 1：Demo Microservices

完成：

```text
Gateway
Order
Inventory
Payment
Redis
Database
```

要求 API 可以真实调用。

测试通过后再进入下一阶段。

------

## Phase 2：Observability

接入：

```text
Metrics
Logs
Trace
```

证明一个 Request 可以：

```text
HTTP
↓
Trace
↓
Logs
↓
Metrics
```

关联起来。

------

## Phase 3：Control Plane

完成：

```text
Alert

Incident

Task

State Machine

Redis

RocketMQ
```

------

## Phase 4：Tool System

实现所有 Read Tool。

先不要实现自动修复。

证明 Agent 能真实查询：

```text
Prometheus
Logs
Trace
K8s
Redis
DB
```

------

## Phase 5：Agent MVP

完成：

```text
Planner
Diagnostic Agent
Evidence
Structured RCA
```

首先支持 3 种故障。

------

## Phase 6：RAG

完成：

```text
Runbook

Hybrid Retrieval

Rerank
```

比较 Retrieval 效果。

------

## Phase 7：Fault Cases

扩展到至少 10 类故障。

------

## Phase 8：Human Approval + Remediation

增加：

```text
restart pod
scale deployment
```

等受控操作。

------

## Phase 9：Verification

实现自动 Recovery Check。

------

## Phase 10：Evaluation

构建：

```text
Dataset
Benchmark Runner
Report
```

------

## Phase 11：Reliability

实现：

```text
Retry
Timeout
Checkpoint
Idempotency
Recovery
```

------

## Phase 12：Benchmark

运行：

```text
API Load Test
Concurrent Incident Test
Agent Evaluation
```

------

## Phase 13：Deployment

完成：

```text
Docker Compose
Kubernetes
CI
```

------

## Phase 14：Documentation

完善全部文档。

------

# 三十二、每阶段必须执行的流程

每完成一个 Phase，必须：

1. 编译。
2. 执行 Unit Test。
3. 执行 Integration Test。
4. 如果存在 E2E，执行 E2E。
5. 检查日志。
6. 检查异常路径。
7. 更新 README。
8. 更新：

```text
docs/progress.md
```

记录：

```text
Done
Current
Next
Known Issues
```

1. 对本阶段进行代码审查。
2. 发现问题立即修复。
3. 测试全部通过后才能进入下一阶段。

------

# 三十三、最终 README

README 必须包括：

```text
项目背景

解决的问题

Architecture Diagram

核心流程

技术栈

Quick Start

Fault Injection Demo

Agent Diagnosis Demo

Tool System

RAG

Security

Evaluation

Benchmark

Testing

Deployment

Project Structure

Future Work
```

------

# 三十四、最终必须生成架构图

使用 Mermaid。

至少生成：

```text
System Architecture

Incident Sequence Diagram

Agent State Machine

Tool Permission Flow

Deployment Architecture
```

------

# 三十五、Benchmark 报告

最终输出：

```text
docs/benchmark.md
```

真实记录：

```text
Root Cause Accuracy

Diagnosis Latency

Tool Calls

Token Usage

Recovery Rate

API QPS

P95

P99
```

同时分析：

```text
瓶颈

优化过程

Before

After

为什么优化有效
```

禁止伪造数据。

------

# 三十六、项目亮点素材

最后根据真实 Benchmark 自动总结：

## 项目简介

控制在：

```text
100~150 字
```

## 项目亮点 Bullet

输出 4 条。

推荐形式：

```text
设计……

针对……问题，通过……优化……

构建……

基于真实 xx 个 Case 评测……
```

所有百分比和指标必须来自真实实验。
