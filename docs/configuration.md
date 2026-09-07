# Configuration

> 与代码对齐版（2026-09-07，P3-DOC-12）。默认值以代码/`application.yml` 为准。

## Environment Variables

| Variable | Used By | Default | Description |
| --- | --- | --- | --- |
| `DB_URL` | control-plane | `jdbc:postgresql://localhost:5432/aisre` | PostgreSQL JDBC URL |
| `DB_USERNAME` | control-plane | `aisre` | DB user |
| `DB_PASSWORD` | control-plane | `aisre` | DB password |
| `REDIS_HOST` | control-plane | `localhost` | Redis host |
| `REDIS_PORT` | control-plane | `6379` | Redis port |
| `SERVER_PORT` | control-plane | `8080` | 业务端口 |
| `MANAGEMENT_PORT` | control-plane | `8085` | 管理/actuator 独立端口（P1-CP-14） |
| `ROCKETMQ_NAME_SERVER` | control-plane | `localhost:9876` | RocketMQ nameserver（producer 直读 env） |
| `AISRE_SECURITY_STRICT` | control-plane | `false` | strict 模式：拒绝默认 secret/口令启动（compose 中为 true） |
| `AISRE_ADMIN_USER/_PASSWORD` | control-plane | `admin`/`admin` | compose strict 下 `aisre-dev-admin-pw` |
| `AISRE_OPERATOR_USER/_PASSWORD` | control-plane | `operator`/`operator` | OPERATOR 口令 |
| `AISRE_VIEWER_USER/_PASSWORD` | control-plane | `viewer`/`viewer` | VIEWER 口令 |
| `AISRE_WEBHOOK_SECRET` | control-plane | 空 | webhook token（空=放行+WARN，仅本地） |
| `AISRE_AGENT_TOKEN` | control-plane | 空 | agent 回调 token（空=fail-closed，P0-05） |
| `AISRE_TASK_LEASE_SECONDS` | control-plane | 600 | 任务租约时长 |
| `AISRE_TASK_MAX_ATTEMPTS` | control-plane | 16 | 毒任务上限（达到→DEAD） |
| `AISRE_TASK_LEASE_RECLAIM_INTERVAL_MS` | control-plane | 60000 | 租约回收扫描间隔 |
| `AISRE_TASK_MAX_SEND_ATTEMPTS` | control-plane | 20 | outbox 补发上限 |
| `LLM_PROVIDER` | agent-runtime | `mock` | `mock` 或 `openai-compatible` |
| `OPENAI_BASE_URL` | agent-runtime | compose 注入 | OpenAI-compatible endpoint |
| `OPENAI_API_KEY` | agent-runtime | empty | LLM API key |
| `OPENAI_MODEL` | agent-runtime | compose 注入 | LLM model |
| `AUTO_CONSUME` | agent-runtime | `false`（compose true） | HTTP 任务轮询消费 |
| `AGENT_TOKEN` | agent-runtime | empty | 轮询/回调携带的 X-Agent-Token |
| `CONTROL_PLANE_URL` | agent-runtime | `http://control-plane:8080` | Control Plane URL |
| `PROMETHEUS_URL` / `LOKI_URL` / `TEMPO_URL` | agent-runtime | compose 注入 | 观测后端 |
| `VERIFICATION_OBSERV_WINDOW_SECONDS` | agent-runtime | `60` | 验证观察窗（P1-AR-06，不计入预算） |
| `VERIFICATION_MAX_ERROR_RATE` | agent-runtime | `0.01` | 确定性判定阈值 |
| `VERIFICATION_MAX_P95_SECONDS` | agent-runtime | `1.0` | 确定性判定阈值 |
| `APPROVAL_TOKEN` | tool-server | `change-me-in-production` | Tool approval token |

## Profiles

当前支持：

- development（默认）
- docker（容器镜像构建时启用：PostgreSQL Driver、Actuator、Prometheus Registry、Flyway）
- integration（Testcontainers 链路 IT）

## Fail Fast

P1-CP-14 已实现 strict 模式启动校验（默认 secret/口令拒绝启动）；`ddl-auto=validate`
保证实体↔Flyway 漂移启动即失败。