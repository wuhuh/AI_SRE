# 需求覆盖清单

| 需求 | 状态 | 说明 |
| --- | --- | --- |
| Control Plane | ✅ | Alert / Incident / Task / Approval / Audit / State Machine |
| Agent Runtime | ✅ | Planner / Diagnostic / Verification / Tool Registry / RAG |
| Tool Calling | ✅ | Prometheus / Loki / Trace / K8s / Redis / DB / MCP Client |
| Evidence | ✅ | 持久化 + API + 前端展示 |
| Human Approval | ✅ | 创建审批 + 决策 + 状态流转 |
| RAG | ✅ | Hybrid Retrieval + 20+ Runbook + Baseline 对比 |
| 故障注入 | ✅ | `/faults` + 脚本 + Chaos Mesh YAML |
| Evaluation | ✅ | 200 Case + Runner + Baseline |
| 测试 | ✅ | 132 = agent 73 + evaluation 12 + Java IT 42 + Playwright 5（2026-09-07 实测；Java 单测含在 mvn test） |
| 前端 | ✅ | 静态 Dashboard + React 工程 |
| Security | ✅ | JWT + Tool 分级 + 审计 + 脱敏 |
| Observability | ✅ | Prometheus / Loki / OTel / Jaeger 配置 |
| Docker Compose | ✅ | 已提供并修复 RocketMQ healthcheck |
| Kubernetes | ✅ | Deployment / Service / HPA / Secret |
| CI | ✅ | GitHub Actions |
| Benchmark | 🟡 | 本地 E2E / Agent 数据已有；Docker k6 数据待补 |
| 真实 Docker E2E | ✅ | 已在 Docker 网络内 3 个故障场景全部通过 |
| React 生产构建 | ✅ | 已在 Docker 内成功 `docker build` |
| Testcontainers | ✅ | maven 容器挂 docker.sock 真跑（testcontainers 1.21.3 + api.version=1.44），39/39 OK（37 既有 + 2 核心链路，P1-T-02），日志 `evidence/mvn_it_p1t02.log`（P1-T-02；P0-11 闭环日志 `mvn_it_docker40.log`） |
| Docker k6 | ✅ | Alert / Incident 压测已执行并记录真实数据 |
| pgvector | ✅ | 已通过真实 pgvector 容器验证 upsert/search |
| RocketMQ 发送/Topic | ✅ | 真实 Topic `aisre-agent-task` 已存在，Producer 在 E2E 中真实发送 |
| RocketMQ Python Consumer | 🟡 | 可选模块已实现，动态库环境未验证 |

## 结论

大部分文档需求已通过代码和本地测试覆盖；剩余项主要是 Docker/构建环境依赖，需要真实 Docker 环境完成最终验收。