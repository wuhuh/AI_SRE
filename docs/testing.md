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
python e2e/local_e2e_runner.py
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