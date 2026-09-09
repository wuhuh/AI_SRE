# Progress

## Done
- Phase 0: Architecture and docs
- Phase 1: Demo microservices (gateway/order/inventory/payment)
- Phase 2: Observability configs (Prometheus, Loki, OTel Collector, Jaeger)
- Phase 3: Control Plane core (alert ingestion, incident state machine, approval, audit)
- Phase 4: Tool system (registry, validation, permission, built-in tools)
- Phase 5: Agent MVP (planner, diagnostic agent, evidence, structured RCA)
- Phase 6: RAG hybrid retriever (BM25 + vector + fusion + rerank)
- Phase 7: Knowledge base with 20 runbooks and postmortems
- Phase 8: Human approval flow and remediation action model
- Phase 9: Verification agent
- Phase 10: Evaluation dataset (200 cases) and runner
- Phase 11: Idempotency keys, persistent task state, retry/timeout abstractions
- Phase 12: Local API load and Agent benchmark runners
- Phase 13: Docker Compose, Kubernetes manifests, CI workflow
- Phase 14: Documentation, coverage matrix, review materials

## Current
- Production Readiness Audit completed
- Baseline Before Hardening recorded
- Stage 2: Flyway migration + configuration docs + secret scan script
- Stage 3 partial: RocketMQ message schema, JSON producer, idempotency store, consumer idempotency
- Stage 4 partial: FileCheckpointStore reconstructs AgentState, crash recovery unit test
- Stage 5 partial: RBAC roles + Approval execution token + Tool allowlist policy + Tool Server token validation
- Stage 6 partial: EmbeddingProvider abstraction + RAG retrieval evaluation metrics
- Stage 7 partial: Evaluation leakage audit + dataset split (dev/val/test)
- Stage 8 partial: Prometheus Alert Rules + Alertmanager + SLO doc
- Stage 9 partial: Docker non-root user for control-plane/agent-runtime/tool-server
- Stage 11 partial: Fault injection expanded to thread_pool/downstream_timeout/memory_pressure
- Stage 13 partial: PostgreSQL backup/restore scripts + docs
- Stage 12 partial: Playwright config + basic browser E2E tests
- Stage 14/15 partial: smoke-test + verify-deployment scripts
- Docs: security / upgrade / failure-mode-matrix / operations / api

## Next
- Real RocketMQ Python Consumer 动态库环境验证
- Chaos Mesh 在 Kubernetes 中实际执行
- Playwright 在真实浏览器环境运行
- Backup/Restore 完整自动化验证

## Known Issues
- Local HTTP server has ~2s request overhead in current Windows environment
- Docker daemon available only through elevated shell in this session
- Some optional modules require Docker/PostgreSQL to run real integration