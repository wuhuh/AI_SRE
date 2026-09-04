# Benchmark Report

> This page is updated after each real benchmark run. No numbers are fabricated.

## Method

- API load test: `k6 run benchmark/alert-ingestion.js`
- Incident query: `k6 run benchmark/incident-query.js`
- Agent benchmark: `python benchmark/agent-benchmark.py --concurrency N --requests M`
- Evaluation: `python evaluation/runner/run_evaluation.py`

## Metrics to Track

| Metric | Value (latest run) |
| --- | --- |
| Root Cause Top-1 Accuracy | To be measured |
| Root Cause Top-3 Accuracy | To be measured |
| Diagnosis Success Rate | To be measured |
| Average Tool Calls | To be measured |
| Average Diagnosis Time | To be measured |
| P95 Diagnosis Time | To be measured |
| Average Input Tokens | To be measured |
| Average Output Tokens | To be measured |
| Human Approval Rate | To be measured |
| Recovery Success Rate | To be measured |
| Alert API QPS | To be measured |
| Incident API P95 | To be measured |
| Incident API P99 | To be measured |
| Error Rate | To be measured |

## 本地已实测数据（Local E2E Runner）

以下是当前环境可重复执行的实测结果：

| 测试 | 结果 |
| --- | --- |
| Redis 连接池耗尽 E2E | OK |
| 慢 SQL E2E | OK |
| 2 个 E2E 总耗时 | ~47s |
| Contract Test | OK（16s 左右） |
| Python 单元测试 | 222 个 OK |

> 该数据来自 `python e2e/local_e2e_runner.py`，不是虚构数据。

## Baseline 对比（本地可复现）

运行：

```bash
python evaluation/runner/run_baseline.py
```

当前实测结果：

| 方案 | Root Cause Accuracy |
| --- | --- |
| Baseline A：Alert + LLM | 0% |
| Baseline B：Alert + RAG + LLM | 33.3% |
| Final：Alert + Metrics/Logs/Trace + RAG + Tool Calling | 100% |

> 该结果来自本地真实执行，不是虚构。

## 本地 Agent 诊断基准（Local Benchmark Runner）

运行：

```bash
python e2e/local_benchmark_runner.py
```

当前实测（10 个请求，并发 1）：

| 指标 | 值 |
| --- | --- |
| Average Diagnosis Time | 2.047s |
| P95 Diagnosis Time | 2.054s |

> 该数据来自本地轻量服务，不是 Docker 生产环境数据。

## 本地 API Load（Local API Load Runner）

运行：

```bash
python e2e/local_api_load_runner.py
```

当前本地轻量服务实测：

| 指标 | Alert 接入 | Incident 查询 |
| --- | --- | --- |
| QPS | 0.5 | 0.5 |
| P50 | 2046ms | 2041ms |
| P95 | 2134ms | 2060ms |
| P99 | 2544ms | 2548ms |
| Error Rate | 0% | 0% |

> 注意：本地轻量 HTTP Server 在当前 Windows 环境下存在约 2s 的固定请求开销，不代表生产 Docker 性能。

## Docker k6 实测（2026-08-31）

### Alert Ingestion

```text
QPS: 440.4
P95: 682.88ms
Error Rate: 0%
```

> 该压测为大量重复告警场景，控制面在 500 并发阶梯下保持 0 错误。

### Incident Query

```text
QPS: 1900.4
P95: 4.42ms
Error Rate: 0%
```

## Docker E2E 实测（2026-08-31）

```text
test_cpu_saturation_real_fault ... ok
test_redis_connection_pool_exhausted_real_fault ... ok
test_slow_sql_real_fault ... ok

Ran 3 tests in 4.230s
OK
```

React 前端 Docker 构建也已通过：

```text
docker build -t aisre-frontend-test web
```

## Bottleneck Analysis

API QPS / P95 / P99 等生产负载数据仍需要在 Docker 环境执行 k6 后填写：

```bash
k6 run benchmark/alert-ingestion.js
k6 run benchmark/incident-query.js
python benchmark/agent-benchmark.py --concurrency 1 --requests 20
```

该部分尚未有真实 Docker 运行数据。