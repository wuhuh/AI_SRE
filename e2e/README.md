# Real Environment E2E Tests

这些测试不是 Mock，而是要求 Docker Compose 完整环境已经启动。

如果服务没有启动，设置 `RUN_E2E=1` 后测试会自动尝试：

```powershell
docker compose up -d --build
```

然后执行：

```powershell
cd agent-runtime
$env:RUN_E2E = "1"
python -m unittest tests.e2e.test_real_faults -v
```

或者：

```powershell
cd agent-runtime
$env:RUN_E2E = "1"
python -m unittest discover -s tests/e2e -v
```

## 无 Docker 环境：本地 E2E Runner

如果当前机器无法使用 Docker，可以用本地轻量 HTTP 服务跑通同一套 E2E 用例：

```powershell
python e2e/local_e2e_runner.py
```

该 runner 会启动：

- Control Plane（本地 18080）
- Agent Runtime（本地 18081）
- payment-service（本地 18001）
- inventory-service（本地 18003）

然后自动执行三个真实故障闭环测试：

1. Redis 连接池耗尽 -> 诊断 -> 恢复 -> 验证 -> RESOLVED
2. 慢 SQL -> 诊断 -> 恢复 -> 验证 -> RESOLVED
3. CPU 饱和 -> 诊断 -> 恢复 -> 验证 -> RESOLVED

## 测试内容

### 1. Redis Connection Pool Exhausted

- 向 `payment-service` 注入 `redis_pool_exhausted` 故障
- 真实请求 `POST /payments` 返回 503
- 发送真实 Alert 到 Control Plane
- 调用真实 Agent Runtime 诊断
- 关闭故障
- 验证 `POST /payments` 恢复为 200
- 调用 Agent 验证，确认 Incident 变为 `RESOLVED`

### 2. Slow SQL

- 向 `inventory-service` 注入 `slow_sql` 故障
- 真实请求 `/inventory/check` 耗时超过 1.5s
- 发送 Alert、Agent 诊断
- 关闭故障
- 验证请求恢复为 200 且耗时低于 1.5s
- Agent 验证后 Incident 变为 `RESOLVED`

### 3. CPU 饱和

- 向 `inventory-service` 注入 `cpu_saturation` 故障
- 真实请求 `/inventory/check` 耗时上升
- 发送 Alert、Agent 诊断
- 关闭故障
- 验证请求恢复为 200 且耗时下降
- Agent 验证后 Incident 变为 `RESOLVED`

## 说明

- 这些测试需要真实访问 Control Plane、Agent Runtime、demo services。
- 如果服务未启动，会自动跳过。
- 建议在完整演示环境上运行，以验证“真实故障 -> 诊断 -> 恢复 -> 验证”闭环。