# Configuration

## Environment Variables

| Variable | Used By | Default | Description |
| --- | --- | --- | --- |
| `DB_URL` | control-plane | `jdbc:postgresql://localhost:5432/aisre` | PostgreSQL JDBC URL |
| `DB_USERNAME` | control-plane | `aisre` | DB user |
| `DB_PASSWORD` | control-plane | `aisre` | DB password |
| `REDIS_HOST` | control-plane | `localhost` | Redis host |
| `REDIS_PORT` | control-plane | `6379` | Redis port |
| `ROCKETMQ_NAME_SERVER` | control-plane | `localhost:9876` | RocketMQ nameserver |
| `LLM_PROVIDER` | agent-runtime | `mock` | `mock` or `openai` |
| `OPENAI_BASE_URL` | agent-runtime | `https://opencode.ai/zen/go/v1` | OpenAI-compatible endpoint |
| `OPENAI_API_KEY` | agent-runtime | empty | LLM API key |
| `OPENAI_MODEL` | agent-runtime | `deepseek-v4-flash` | LLM model |
| `AUTO_CONSUME` | agent-runtime | `true` | Enable HTTP task consumer |
| `CONTROL_PLANE_URL` | agent-runtime | `http://control-plane:8080` | Control Plane URL |
| `PROMETHEUS_URL` | agent-runtime | `http://prometheus:9090` | Prometheus URL |
| `LOKI_URL` | agent-runtime | `http://loki:3100` | Loki URL |
| `TEMPO_URL` | agent-runtime | `http://jaeger:16686` | Trace URL |
| `APPROVAL_TOKEN` | tool-server | `change-me-in-production` | Tool approval token |
| `AISRE_ADMIN_USER` | control-plane | `admin` | Admin username |
| `AISRE_ADMIN_PASSWORD` | control-plane | `admin` | Admin password |
| `AISRE_OPERATOR_USER` | control-plane | `operator` | Operator username |
| `AISRE_OPERATOR_PASSWORD` | control-plane | `operator` | Operator password |
| `AISRE_VIEWER_USER` | control-plane | `viewer` | Viewer username |
| `AISRE_VIEWER_PASSWORD` | control-plane | `viewer` | Viewer password |

## Profiles

当前支持：

- development（默认）
- docker（Docker Compose 构建时启用，包含 PostgreSQL Driver、Actuator、Flyway、Prometheus Registry）
- integration（Testcontainers）

## Fail Fast

关键配置缺失时服务应快速失败。后续将为 Control Plane / Agent Runtime 增加启动配置校验。