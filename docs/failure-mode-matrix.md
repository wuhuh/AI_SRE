# Failure Mode Matrix

| Component | Failure | Impact | Detection | Recovery |
| --- | --- | --- | --- | --- |
| Control Plane | Down | 无法 API / 无法创建 Incident | Health Monitor / Smoke Test | 重启 Deployment |
| Agent Runtime | Down | 无法诊断 | Health Monitor | 重启 Deployment |
| Tool Server | Down | 无法执行修复 | Health Monitor | 重启 Deployment |
| PostgreSQL | Down | 数据不可用 | Health Monitor / Alert | 恢复 Volume / Restore |
| Redis | Down | 去重/缓存不可用 | Health Monitor | 重启 Redis |
| RocketMQ | Down | 任务无法投递 | Consumer Lag / Health | 重启 Namesrv/Broker |
| Prometheus | Down | 无法获取指标 | Alertmanager | 重启 Prometheus |
| Loki | Down | 无法查询日志 | Health | 重启 Loki |
| Jaeger | Down | 无法查询 Trace | Health | 重启 Jaeger |
| LLM Provider | Timeout/5xx | Agent fallback | Agent Metrics | Retry / Fallback / Human Escalation |