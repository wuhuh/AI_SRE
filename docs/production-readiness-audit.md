# Production Readiness Audit

> 状态标识：
> - ✅ READY
> - 🟡 PARTIAL
> - ❌ MISSING
> - 🔴 BROKEN
> - ❓ UNKNOWN

| 领域 | 状态 | 说明 |
| --- | --- | --- |
| Application Architecture | 🟡 | 分层已完整，但部分模块仍依赖本地/模拟实现 |
| Configuration | 🟡 | 支持 `.env` 和部分环境变量；缺少 Spring Profile 全量分层 |
| Secrets | 🟡 | `.env.example` 已提供；仍需确认无真实 Secret 入库 |
| Authentication | 🟡 | JWT 已实现；缺少用户体系与角色登录 |
| Authorization / RBAC | ❌ | 只有登录/未登录，缺少 VIEWER / OPERATOR / ADMIN |
| Database | 🟡 | JPA 自动建表；缺少 Flyway/Liquibase Migration |
| Redis | ✅ | 去重、缓存、限流基础能力存在 |
| RocketMQ | 🟡 | Producer/Topic 已验证；Python Consumer 未真正落地 |
| Agent Runtime | 🟡 | 核心 Agent 已实现；Durable Execution 仍需增强 |
| Tool Security | 🟡 | RiskPolicy 已有；Tool Allowlist 不完整 |
| MCP | ✅ | `/mcp` JSON-RPC 和 MCP Client 已实现 |
| RAG | 🟡 | Hybrid Retriever 已实现；真实 Embedding 未接入 |
| Evaluation | 🟡 | 200 Case + Baseline；缺少 Held-out Split 和 Leakage 审计 |
| Observability | 🟡 | Prometheus/Loki/Jaeger 配置存在；Agent 自身指标不完整 |
| Alerting | 🟡 | Java HealthMonitor 有；Prometheus Alert Rules + Alertmanager 未完整 |
| Docker | 🟡 | Compose 可跑；镜像 Hardening 不完整 |
| Kubernetes | 🟡 | 基础 Manifest 存在；RBAC/NetworkPolicy/PDB/Ingress 不完整 |
| Storage | 🟡 | Postgres Volume 有；RocketMQ/Grafana 持久化需确认 |
| Reliability | 🟡 | Timeout/Retry 有；Crash Recovery E2E 未完成 |
| Backup / Recovery | ❌ | 缺少备份/恢复脚本与测试 |
| Security | 🟡 | JWT/Risk/Approval 有；RBAC/Approval Token/Secret Scan 不完整 |
| CI | 🟡 | Java/Python/Docker 有；Frontend/Security/K8s Validate 缺失 |
| CD | ❌ | 无镜像推送/不可变 Tag |
| Performance | 🟡 | k6 有数据；Agent 并发/容量边界未测 |
| Chaos Engineering | ❌ | 只有 YAML，未真正执行 |
| Frontend | 🟡 | 新 Dashboard 已重构；Browser E2E 缺失 |
| Documentation | 🟡 | 已有较多文档；部署/操作/升级文档不完整 |

## 关键风险

1. Agent Runtime 的任务执行仍以 HTTP polling 为主，RocketMQ 正式消费链路未成为主链路。
2. AgentState 虽有 Checkpoint 文件，但未在 Docker 生产环境中验证 Crash Recovery。
3. 审批系统缺少一次性 Execution Token 和参数绑定，存在复用风险。
4. RBAC 未实现，所有登录用户权限一致。
5. 数据库没有正式 Migration，依赖 JPA `ddl-auto=update`。
6. Tool Server 在 K8s 中的 RBAC 和 NetworkPolicy 未配置。
7. Prometheus Alertmanager 告警链路未完整打通。
8. Backup / Restore 缺失。
9. 浏览器 E2E 缺失。