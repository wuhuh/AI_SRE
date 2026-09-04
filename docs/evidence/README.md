# docs/evidence — 验证证据归档

本目录存放被 docs/ 引用的验证证据原始文件（副本；原文件位于仓库根目录且已被 .gitignore 忽略）。

| 文件 | 引用文档 | 内容 |
|---|---|---|
| docker_e2e.log | docker-validation.md / implemented-features.md | Docker 环境 3 个真实故障 E2E（Ran 3 tests OK）。注意：日志显示 cpu/slow_sql 场景 root_cause 均为 redis_connection_pool_exhausted（错诊，见 audit P0-01/DOC-03） |
| docker_ps2.txt | docker-validation.md | compose 16 服务运行快照（postgres/redis/namesrv healthy） |
| k6_alert3.log | benchmark.md | alert ingestion 压测：440 QPS @ P95 682.88ms（**超出脚本自设 500ms 阈值，k6 以错误退出**，文档须如实记录） |
| k6_incident.log | benchmark.md | incident query 压测：1900 QPS @ P95 4.42ms（通过） |
| mvn_it_dind6.log | DOC-01 证据 | Testcontainers 运行日志：**BUILD FAILURE**（ControlPlaneIntegrationTest `ContainerLaunchException: redis:7-alpine`）——证明"Testcontainers 通过"为虚假记录 |
| pgvector_test.log | docker-validation.md | pgvector 扩展可用性验证（"pgvector ok doc1"） |
| rocketmq_topics.txt | docker-validation.md | broker topic 列表（含 aisre-agent-task） |

来源：2025-08-31 Docker/DIND 验证会话（见 docs/docker-validation.md）。
