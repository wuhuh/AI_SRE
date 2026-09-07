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
| Python 单元测试 | 73 个 OK（agent-runtime，2026-09-07 实测） |

> 该数据来自 `python e2e/local_contract_smoke.py`，不是虚构数据。

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
## Root Cause 诊断评测（2026-09 重测，P0-03 修复后）

> ⚠️ 本节取代上方 "Baseline 对比（本地可复现）" 的结论地位：那份 0%/33.3%/100%
> 来自 `run_baseline.py` 的 3 个手写 case + 自写关键词 LLM + 把答案注入 tool_hint，
> 属于机制示意（sanity check），**不是能力测量**，不得作为准确率引用。

修复后的正式评测（`evaluation/runner/run_evaluation.py`）：

- 输入无泄漏：alert 由中性 symptom 档案构造，fault_type（答案标签）绝不进入输入
- 打分：canonical 标签精确匹配；Top-3 基于 agent 真实 alternatives 候选
- 数据集：test split（20/200，`evaluation/splits/test.json`）
- 原始结果：`evaluation/results/eval_20260904T183015Z_test_mock.json`、
  `evaluation/results/eval_20260904T182953Z_test_openai.json`

| Provider | Top-1 | Top-3 | Unknown Rate | Evidence Recall | 备注 |
|---|---|---|---|---|---|
| mock | 0.05 | 0.05 | 0.00 | 0.07 | mock 恒答 redis 的机率基线（诚实值） |
| openai (deepseek-v4-flash) | **0.70** | 0.70 | 0.30 | 0.00 | 14/20 命中；6/20 降级为 unknown（无自信错答） |

已知短板（后续改进方向）：① 6 个 unknown 全部集中在 cache/db 层类故障
（redis/slow_sql/mq_backlog），为 LLM 循环超步/解析失败，非错误结论；
② Evidence Recall 0.0 —— LLM 声明的证据 key 与期望 key 零交集；
③ Top-3 ≡ Top-1：alternatives 从未救回 miss。

## 真实故障评测（2026-09，P0-08 一期，Docker compose 环境）

> 本节是第一次在**真实注入的故障**上测量（此前评测的"故障"只是测试数据里的标签，
> 系统里并没有故障在发生）。注入方式：
> - `inventory-service` `cpu_saturation`：uvicorn 进程内 sha256 busy-loop
>   （进程内真实计算），持续灌压 `avg(rate(process_cpu_seconds_total))=0.83`；
> - `payment-service` `redis_pool_exhausted`：故障开关使 /payments 全量 503，
>   5xx 4.6/s 真实产生。
> 评测期间两个故障**真实存在**于 compose 栈中，agent 的工具读到的都是真实
> Prometheus/Loki/Jaeger 数据。评测后故障关闭，CPU 回落 0.0014（已验证恢复）。
>
> 运行方式（真实 LLM = openai/deepseek-v4-flash，宿主机 agent:18081）：
> ```bash
> python evaluation/runner/run_evaluation.py --splits all --provider openai \
>   --agent-url http://127.0.0.1:18081 \
>   --types cpu_saturation,redis_connection_pool_exhausted \
>   --services inventory-service,payment-service --tag real-fault-final2
> ```

| 故障类（case 数） | Top-1 | 备注 |
|---|---|---|
| cpu_saturation（7） | **7/7 (100%)** | 真实 CPU 指标可观测，全部命中 |
| redis_connection_pool_exhausted（7） | 1/7 | 证据主要在应用日志；Top-3 共 2/7 |
| **合计（14）** | **Top-1=0.571，Top-3=0.643，Unknown=0.214** | 工具成功率 100% |

迭代轨迹（同 14 case，逐项工程修复的效果）：

| 版本 | Top-1 | 修复内容 |
|---|---|---|
| real-fault (v1) | 0.357 | 首轮：LLM 15s 读超时全量降级 + Jaeger 400 + redis 工具缺失 |
| real-fault-v4 | 0.571 | LLM 超时跟随诊断预算（150s） |
| real-fault-final2 | **0.571**（Top-3 0.643） | redis 工具别名 + 编造工具名收敛守卫 |

与合成评测（上方 test split 0.70）对比：真实故障 Top-1 略低但量级一致——
差异主要来自 redis 类（合成评测里 mock/LLM 可凭标签先验，真实故障必须从
可观测数据推出）。已知短板：Evidence Recall 仍 0.00（LLM 证据 key 为
`tool:N` 序号，与期望的语义 key 零交集——评测口径问题，见 P2-FI-10）。
原始结果：`evaluation/results/eval_20260905T165905Z_all_openai_real-fault-final2.json`
（及 v1–final 全系列）。
