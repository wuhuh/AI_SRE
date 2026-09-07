# Production Readiness Audit

> 状态标识：✅ READY / 🟡 PARTIAL / ❌ MISSING / 🔴 BROKEN
> 与代码对齐版（2026-09，P0/P1 收尾后重写；原版见 docs/baseline-before-hardening.md）。

| 领域 | 状态 | 说明 |
| --- | --- | --- |
| Application Architecture | 🟡 | 诊断/审批/修复/验证全链路落地；k8s 修复执行器在无真实集群下未实测 |
| Configuration | 🟡 | `.env` + strict 模式（禁默认 secret/口令）；Spring Profile 分层未做 |
| Secrets | 🟡 | strict 校验已上；真实 key 轮换待做（P3-DOC-11） |
| Authentication | ✅ | JWT + BCrypt（明文兼容迁移期）+ strict 模式 |
| Authorization / RBAC | ✅ | VIEWER/OPERATOR/ADMIN + 拦截器（读≥VIEWER/写 ADMIN-OPERATOR/webhook/agent token） |
| Database | ✅ | Flyway 单轨 V1..V7 + `ddl-auto=validate`（IT 走真实迁移路径；CI 断言对齐） |
| Redis | ✅ | 去重/缓存/限流；Redis 故障降级 fail-open（CP-15） |
| RocketMQ | 🟡 | outbox + afterCommit + 扫描器补发（CP-07）；**直连消费未接线**，生产路径=轮询 |
| Agent Runtime | 🟡 | 确定性验证/注入防护/工具超时/重试边界落地；checkpoint 崩溃恢复 E2E 未验证 |
| Tool Security | 🟡 | RiskPolicy + principals + 超时强制；allowlist 依赖部署环境 |
| MCP | ✅ | `/mcp` JSON-RPC 与 client 实现（去留决策 P2-AR-11） |
| RAG | 🟡 | Hybrid 关键词检索可用；真实 embedding 未接入 |
| Evaluation | 🟡 | 真实故障+真实 redis 池 eval：整体 57.1%、cpu 7/7；Evidence Recall 指标语义待修（P2-FI-10） |
| Observability | 🟡 | traces+metrics 全链路通；平台自身指标不全（P2-FI-08） |
| Alerting | ✅ | 7 条规则对真实 series 验证；AM→CP webhook（secret）+ 聚合链路通 |
| Docker | 🟡 | 21 容器 compose 可复现；镜像 hardening/rootless 未做 |
| Kubernetes | 🟡 | manifest 存在；RBAC/NetworkPolicy/PDB 未实测（P0-10/P2-K8S-01，需真实集群） |
| Storage | 🟡 | pg 卷持久；AM/Grafana 持久化未确认 |
| Reliability | 🟡 | outbox/租约回收/毒任务 DEAD/条件更新/幂等键齐；chaos 未实测 |
| Backup / Recovery | 🟡 | 脚本与文档在（backup-restore.md）；未演练归档（P3-备份演练） |
| Security | 🟡 | RBAC/webhook secret/actuator 分端口/strict 齐；**静态 token 可重放** |
| CI | ✅ | java unit + integration（testcontainers）+ ruff + web-build + docker-build |
| CD | ❌ | 无镜像推送/不可变 tag |
| Performance | 🟡 | k6 有数据；并发/容量边界未测 |
| Chaos Engineering | ❌ | 仅 YAML，未执行（P2-FI-07） |
| Frontend | 🟡 | React 轨 + auth headers；Playwright 冒烟缺失（P2-FE-02） |
| Documentation | ✅ | 本次已与代码对齐（architecture/security/本文件） |

## 关键风险（现状）

1. 任务分发主链路是控制面轮询；RocketMQ 直连消费未接线（消费语义与 DLQ 已在轮询侧落地）。
2. Checkpoint 文件型崩溃恢复未在容器环境验证。
3. 静态共享 token（agent/webhook/approval）可重放，生产需换短期凭证或 mTLS。
4. 脱敏工具未接入任何生产路径（工具结果原样入库）。
5. K8s 修复执行与 RBAC/NetworkPolicy 未实测（依赖真实集群）。
6. 无 CD：镜像无不可变 tag/推送；备份未演练。
7. 浏览器 E2E（Playwright）缺失。
