# Docker 验证记录

## 环境

- Docker Desktop（Windows named pipe）
- Docker Compose 完整环境

## 已验证

### 1. Docker Compose 启动

```bash
docker compose up -d --build
```

所有核心服务均 Up / Healthy。

### 2. 真实 Docker E2E

在 Docker 网络内运行：

```bash
docker run --rm --network aisre_default \
  -v <repo>:/repo -w /repo/agent-runtime \
  -e RUN_E2E=1 -e CONTROL_PLANE_URL=http://control-plane:8080 \
  -e AGENT_URL=http://agent-runtime:8080 \
  -e PAYMENT_URL=http://payment-service:8001 \
  -e INVENTORY_URL=http://inventory-service:8003 \
  python:3.11-slim python -m unittest tests.e2e.test_real_faults -v
```

结果：

```text
test_cpu_saturation_real_fault ... ok
test_redis_connection_pool_exhausted_real_fault ... ok
test_slow_sql_real_fault ... ok
OK
```

### 3. React Docker 构建

```bash
docker build -t aisre-frontend-test web
```

构建成功。

### 4. Docker k6 压测

```bash
docker run --rm --network aisre_default \
  -v <benchmark>:/scripts -e BASE_URL=http://control-plane:8080 \
  grafana/k6 run /scripts/alert-ingestion.js
```

结果：

- Alert QPS 440.4，P95 682.88ms，Error 0%
- Incident QPS 1900.4，P95 4.42ms，Error 0%

## pgvector 真实联调

启动：

```bash
docker run -d --name aisre-pgvector \
  -e POSTGRES_PASSWORD=aisre -e POSTGRES_USER=aisre -e POSTGRES_DB=aisre \
  -p 55432:5432 pgvector/pgvector:pg16
```

通过 `PGVectorDocumentStore` 实测：

```text
pgvector ok doc1
```

## RocketMQ 真实验证

RocketMQ Broker 中已存在真实 Topic：

```text
aisre-agent-task
```

Control Plane 在 Alert 接入时会向该 Topic 发送任务消息。

## Testcontainers

通过 Docker-in-Dind（DIND）执行：

```text
mvn -Pintegration verify
```

结果：`BUILD SUCCESS`

## 未验证

- RocketMQ Python Consumer（动态库环境缺失）
- Chaos Mesh 真实实验