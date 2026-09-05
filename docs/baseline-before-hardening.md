# Baseline Before Hardening

> 本文记录 Production Readiness 增强前的真实测试与 Benchmark 基线。
> 之后所有优化必须与本文对比。

## Environment

| Item | Value |
| --- | --- |
| Git Commit | N/A（当前目录不是 Git 仓库） |
| OS | Windows |
| Java | 17 |
| Python | 3.13（本地）/ 3.11（容器） |
| Docker | Docker Desktop |
| CPU / Memory | 未记录详细规格 |

## Test Baseline

| Test | Result |
| --- | --- |
| Java Unit Tests | Passed |
| Python Unit Tests | 240 passed |
| Local Contract Test | Passed |
| Local E2E | 3 passed |
| Docker E2E | 3 passed |
| Testcontainers | ✅ 通过（testcontainers 1.21.3 + api.version=1.44，37/37 OK；闭环日志 `evidence/mvn_it_docker40.log`） |
| pgvector Real Integration | Passed |
| RocketMQ Topic/Producer | Passed |
| React Docker Build | Passed（此前验证） |

## Performance Baseline

### Alert Ingestion（Docker k6）

| Metric | Value |
| --- | --- |
| QPS | 440.4 |
| P95 | 682.88ms |
| Error Rate | 0% |

### Incident Query（Docker k6）

| Metric | Value |
| --- | --- |
| QPS | 1900.4 |
| P95 | 4.42ms |
| Error Rate | 0% |

## Evaluation Baseline

| 方案 | Accuracy |
| --- | --- |
| Baseline A（Alert + LLM） | 0% |
| Baseline B（Alert + RAG + LLM） | 33.3% |
| Final（Full Tool Calling） | 100% |

> 注意：当前 Final 100% 需要审计是否存在 Evaluation Leakage 或规则 fallback 直接映射问题。

## Known Gaps

- Agent Durable Execution / Crash Recovery 未验证
- RocketMQ 正式 Consumer 未成为主链路
- RBAC 未实现
- Approval Execution Token 未实现
- Database Migration 未实现
- Backup / Restore 未实现
- Prometheus Alertmanager 链路未完整