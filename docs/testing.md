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

- 真实运行记录（2026-09-07）：
  - run `34146753562`（a273d56）：**5 过**（java-build / web-build /
    secret-scan / k8s-validate / docker-build），2 挂——ruff 版本漂移
    （已 pin 0.16.6 修复）；java-integration 待日志定位。
  - run `34147717090`（7f5a9bc）：**6 过**（ruff 修复生效），
    java-integration 仍挂——本地同镜像 42/42 绿两次，属 CI 环境差异，
    待 Actions 页日志定位（logs 下载需 admin 权限，匿名不可读）。
- push 触发的 job：java-build / java-integration / python-lint-and-test /
  web-build / secret-scan / k8s-validate / docker-build；nightly-integration
  由 schedule cron（每日 03:00 UTC）触发。
- 各 job 关键步骤的本地等价实测对照见 `docs/ci-activation.md`。
