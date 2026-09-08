# 测试说明

## 单元测试

```bash
cd control-plane && mvn -o test
cd agent-runtime && python -m unittest discover -s tests
```

## Contract Test

```bash
cd agent-runtime && python -m unittest tests.test_local_contract -v
```

## 本地完整 E2E（无需 Docker）

```bash
python e2e/local_contract_smoke.py
```

覆盖：

- Redis 连接池耗尽
- 慢 SQL
- CPU 饱和

## 本地 Benchmark

```bash
python e2e/local_benchmark_runner.py
python e2e/local_api_load_runner.py
```

## Baseline 对比

```bash
python evaluation/runner/run_baseline.py
```

## 一键运行全部本地测试

```bash
python run_all_local_tests.py
```

## Docker / 生产验证

```bash
docker compose up -d --build
cd agent-runtime
$env:RUN_E2E = "1"
python -m unittest tests.e2e.test_real_faults -v
```
## CI（GitHub Actions，P2-CI-03）

- 真实运行记录（2026-09-07/08，共 8 轮）：
  - run `34146753562`（a273d56）：5 过 2 挂——ruff 版本漂移（pin 0.16.6
    修复）+ java-integration。
  - run `34147717090`→`34184992121`：java-integration 连挂 4 轮，经
    ::error:: 注解回传的 ingest 日志定位根因——**ServiceHealthMonitor
    在 IT 上下文每 15s 探活，CI runner 上无 compose demo 服务 → 探活
    失败发 service_down 告警 → 顶高 Chain 刚建的 incident 的 alertCount
    （本地绿只因 compose 服务恰好可达）**。
  - 修复：`@ConditionalOnProperty(name="health.monitor.enabled",
    matchIfMissing=true)`（生产不变）；Chain IT 显式关闭；另加 Chain
    dedup redis 探针（fail-open 时响亮报根因）+ CI 失败注解回传管道。
  - 本地模拟 CI（停 compose demo 服务）42/42 绿 → run `a1f64ba` **全绿
    7/7**（java-build/java-integration/python-lint-and-test/web-build/
    secret-scan/k8s-validate/docker-build）。
  - nightly-integration（cron 03:00 UTC）尚未到首跑时刻，首跑后回填。
- push 触发的 job：java-build / java-integration / python-lint-and-test /
  web-build / secret-scan / k8s-validate / docker-build；nightly-integration
  由 schedule cron（每日 03:00 UTC）触发。
- 各 job 关键步骤的本地等价实测对照见 `docs/ci-activation.md`。
