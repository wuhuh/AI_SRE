# AI SRE 项目全面技术审计（Technical Audit + Improvement Roadmap 输入）

- 审计日期：2025-09（基于代码快照，工作区含未提交修改）
- 审计方式：9 个 Pass（Architecture / Control Plane / Agent Runtime / Tool·MCP / RAG·Evaluation / Observability·Fault / Docker·K8s·CI / Testing·Benchmark·Security / Cross-module），全部结论基于真实代码与留存运行日志，禁止性要求（只读、不改业务代码）已遵守。
- 审计者：主审计 + 4 个并行子审计（Control Plane、故障注入与可观测性、前端/测试/CI、文档真实性），主审计亲读 Agent Runtime / Tool Server / Evaluation / 部署与配置核心。
- 证据约定：所有结论附 `file:line`。凡未能在代码中确证的，明确标注 `NEEDS VERIFICATION`。

---

# Executive Summary

这个项目「形已立，神未立」。

**架构骨架是真实且合理的**：告警接入 → 去重聚合 → Incident → 任务分发 → Agent 诊断（Planner/Diagnostic/Verification）→ Evidence 落库 → 审批 → 修复 → 验证 → Report 的完整闭环在代码里逐环存在，Flyway schema、审计日志、SSE、前端控制台、Docker Compose 全栈都能启动。**可观测性中分布式链路追踪是全项目最真实的部分**（OTLP→Collector→Jaeger，W3C traceparent 跨服务传播实测成立）。

**但三个「支点级」的问题让项目当前不能自称 AI SRE：**

1. **AI 核心是剧场**。诊断结论主要来自 `diagnostic.py:174-217` 的关键词规则兜底（"summary 里有 redis → redis_connection_pool_exhausted"），LLM 失败时默认置信度写死 0.8、无证据时伪造 `source="rule"` 的伪证据；工具调用参数硬编码 `payment-service` 和固定 PromQL（`diagnostic.py:219-237`），对 inventory-service 的告警也去查 payment 的指标；tool-server 的 k8s/db 端点返回 `dryRun:true` 和硬编码假数据（`tool-server/app.py:86-97`）；Loki 无任何日志写入者（query_logs 恒为空）。**"Evidence-Driven RCA" 的证据层大面积虚假或断链。**
2. **Evaluation 结构性失真**。`run_evaluation.py:53` 把 `fault_type`（答案本身）写进告警 summary，`:93` 用双向子串匹配放水，且标签空间不匹配（agent 输出 snake_case、期望是自然语言句子）——按当前打分逻辑实测模拟为 **0/200**；`run_baseline.py` 的 0%/33.3%/100% 是 3 个手写 case + 自写关键词 LLM + 把答案注入 tool_hint 的自证产物；MockLLM 硬编码 redis 答案（`mock.py:36-45`）与 200 个 case 的 expected_evidence 完全一致。**当前没有任何一个可信的准确率数字。**
3. **可靠性与安全语义多为装饰**。任务无 claim/lease（K8s HPA 多副本必然重复诊断）、agent 回调免鉴权且无幂等（重放即重复执行修复）、审批与执行参数脱钩（审批 "scale payment" 实际执行 `default/default` 硬编码 URL）、RiskPolicy 对未知动作默认 LOW_RISK（fail-open）、JWT 过期校验因解析 bug **从不生效**、checkpoint 的 load 在生产路径零调用（crash recovery 不存在）、RocketMQ 无消费者（真实链路是 HTTP 轮询）。

另外：**整个仓库 0 个 git commit**（`git log --all` 为空，全部文件 untracked），与 AGENTS.md 自身的 Git 工作流要求相悖；CI workflow 从未被触发过。

**一句话定位**：这是一个「闭环形态完整、组件边界清晰、但证据链与评测可信度尚未成立」的 Production-like 学生项目。按下面 2 周 Roadmap 修完 P0（约 10 个工作日），项目性质会从「演示」变为「可信」。

Production Readiness 总分：**3.9 / 10**（评分卡见下）。

---

# Project Map（以实际代码为准）

```text
                          ┌────────────────────────────────────────────┐
 Alertmanager(v0.27) ─────│► Control Plane  Java17/SpringBoot3.4 :8080 │
  8条alert rules          │  AlertController → AlertService            │
  webhook(契约断裂 P0-07) │   └ Redis SETNX dedup(5min) + LIKE 聚合(10min)│
                          │  IncidentRepository(PG16, Flyway V1/V2     │
                          │   + hibernate ddl-auto:update 双轨)         │
                          │  RocketMqAgentJobProducer ──► broker        │
                          │   (aisre-agent-task；⚠ 无任何消费者)         │
                          │  AgentTaskController /tasks/pending ◄───────┼──┐ (实际链路:
                          │  IncidentController 13端点 / StreamController│  │  HTTP 轮询)
                          │  ApprovalController / Dashboard / Report    │  │
                          │  AgentResultService(回调落库+auto-approval) │  │
                          │  RemediationExecutor ──HTTP──► tool-server  │  │
                          │  IncidentEventService(单实例SSE) / Auth(JWT)│  │
                          └───────────────┬────────────────────────────┘  │
                                          │ 2026行Python                    │
                          ┌───────────────▼────────────────────────────┐  │
                          │ Agent Runtime FastAPI :8081                │──┘
                          │  consumer.py(AUTO_CONSUME 线程,3s轮询)      │
                          │  AgentRunner: Planner→Diagnostic(12步/15s)  │
                          │   →VerificationAgent(LLM判定,无SLI)         │
                          │  ToolRegistry(Cached, 6工具) ──直连──┐      │
                          │  HybridRetriever(hash-embedding BM25 │      │
                          │   +cosine+overlap rerank, 20 runbooks)│     │
                          │  MockLLMProvider(默认) / OpenAI兼容    │     │
                          │  FileCheckpoint/FileIdempotency(进程内)│     │
                          └──────────────┬───────────────────────┘      │
                                         │ HTTP                           │
   Prometheus(:9090) ◄─scrape─ demo-services(FastAPI ×4, :8000-8003)     │
   (agent-runtime/tool-server 不被 scrape)                               │
   Loki(:3100) ← ⚠ 零写入者(无promtail/无driver)                          │
   otel-collector → Jaeger(:16686) ← demo traces(真实)                   │
   Grafana(:3000, 0 dashboard)   tool-server(:8082) ◄────────────────────┘
                                 redis(真实) / k8s(dryRun假) / db(硬编码假)
   前端 nginx:8083 (vanilla app.js 可用; React版死代码)
   PG(:5432) Redis(:6379) RocketMQ(namesrv+broker) ← compose 全家桶
```

模块清单（职责 / 语言 / 规模 / 入口 / 依赖）：

| 模块 | 职责 | 语言/框架 | 规模 | 入口 | 依赖 |
|---|---|---|---|---|---|
| control-plane | 告警/Incident/审批/修复/审计/SSE | Java 17, Spring Boot 3.4, JPA | 70 文件 3564 行 | `AiSreApplication` | PG, Redis, RocketMQ(client), tool-server |
| agent-runtime | Agent 诊断/验证/RAG/消费 | Python 3.11, FastAPI | app ~2000 行, tests ~2500 | `app.main:app` | Prometheus/Loki/Jaeger/tool-server/CP/LLM API |
| tool-server | Tool Gateway (MCP-ish) | Python FastAPI | 96 行 | `app.py` | Redis(真实), (k8s/db 为假数据) |
| demo-services | 故障演示微服务 ×4 | Python FastAPI, OTel | ~400 行 | 各 `app.py` | Redis(payment), 彼此 |
| evaluation | 200 case + runner ×5 | Python | ~700 行 | `run_evaluation.py` | agent-runtime API |
| fault-injection | 故障开关 CLI + chaos YAML | Python/YAML | ~130 行 | `inject_fault.py` | demo services |
| observability | Prom/AM/Loki/OTel/Grafana 配置 | YAML | 6 文件 | compose 挂载 | — |
| web | 控制台（vanilla 可用 + React 死代码） | JS/React | ~1000 行 | nginx | CP API |
| deploy/k8s | 8 个 manifest | YAML | — | kubectl | — |
| .github | CI | YAML | 1 workflow | push/PR | — |

调用关系与模块间数据流如上图；**注意图中标 ⚠ 的三处断点**（MQ 无消费者、AM 契约断裂、Loki 无写入者）是本审计最重要的结构性发现。

---

# Feature Completeness Matrix

图例：DOCUMENTED < IMPLEMENTED < TESTED < E2E VERIFIED < PRODUCTION READY。判级依据来自四路子审计 + 主审计亲读，代码证据见对应 Findings 章节。

| 能力 | 等级 | 关键依据 / 主要缺口 |
|---|---|---|
| Alert ingestion | E2E VERIFIED | `AlertService.ingest` 真实落库+回填；**但 AM webhook 契约断裂（P0-07）、无输入校验、无 webhook secret** |
| Alert deduplication | IMPLEMENTED | Redis SETNX EX 正确；**结果只作 flag 不 gate；Redis 挂 → 告警入口 500（fail-closed）** |
| Alert aggregation | IMPLEMENTED | 10min 窗口；**LIKE 模糊错绑 + 并发重复创建 incident** |
| Incident management | IMPLEMENTED | 13 端点齐全；**无 @Version、findAll 全表扫描** |
| Incident state machine | TESTED | 纯函数 + 3 单测（全项目唯一达 TESTED）；**存在 bypass 与非法流转静默忽略** |
| Agent task lifecycle | IMPLEMENTED | 仅 QUEUED→人工 complete；**幂等键含 UUID 失效、无 RUNNING/FAILED、无 claim** |
| Evidence management | IMPLEMENTED | 落库+查询 API；**taskId 恒 null、证据内容大面积伪造/断链（P0-01/02/10）** |
| Tool call records | IMPLEMENTED | 落库+查询；**riskLevel 恒 READ_ONLY 失真** |
| Approval | IMPLEMENTED | 创建/决策/token 流程在；**无过期、REJECT 悬挂、并发竞态、与执行参数脱钩（P0-04）** |
| Remediation | IMPLEMENTED | HTTP 执行+落库；**硬编码目标+未知动作兜底 restart_pod、事务内副作用、tool-server dryRun（P0-04/10）** |
| Verification | COSMETIC→IMPLEMENTED | 触发链路在；**LLM 判定无确定性 SLI、无观察窗、从空 state 起跑** |
| Audit log | IMPLEMENTED | 全动作埋点；**同步同事务（回滚即丢）、actor 可伪造** |
| SSE | IMPLEMENTED | 单实例可用；**无心跳/重放/多实例** |
| Incident report | IMPLEMENTED | 现算 markdown；不持久化 |
| Dashboard API | E2E VERIFIED | summary/services 可用；findAll 扫描、健康串行 12s |
| Authentication | IMPLEMENTED | HS256 签名+constant-time；**exp 永不生效（P0-06）、默认密钥、默认口令 admin/admin** |
| Authorization | IMPLEMENTED | 仅 approvals/transition 受控；**全部 GET、agent 回调、tasks/complete、actuator 裸奔** |
| RBAC | DOCUMENTED | 三角色定义在；VIEWER≈匿名，无资源级权限 |
| Planner | COSMETIC | 产出=工具名列表，fallback 固定 4 步；不产生服务/查询参数 |
| Diagnostic Agent | PARTIAL | 循环/上限/超时在；**结论来自规则兜底、工具参数硬编码（P0-01/02）** |
| Checkpoint / crash recovery | COSMETIC | 仅 run 后 save；**load 生产零调用、无原子写、verify 从空 state 起（P0-09）** |
| LLM Provider | PARTIAL | OpenAI 兼容客户端可用；**无重试/退避/熔断（Retry 存在但未接线）、Timeout 空壳** |
| RAG (hybrid) | PARTIAL | BM25+融合+rerank 代码真实；**hash 假 embedding、无 chunking、pgvector 未接线、无检索指标产出** |
| MCP | COSMETIC | 手写 JSON-RPC 端点；主链路零调用、多数工具 dryRun |
| RocketMQ | PARTIAL | producer 真实+broker 部署；**consumer 依赖缺失从未启用，真实链路是轮询** |
| Prometheus→AM→CP | PARTIAL | 前三段接线真实；**最后一环契约断裂；3/8 规则引用幻影 metric** |
| Tracing | **REAL** | OTLP→collector→Jaeger + W3C 传播真实可用（全项目最佳） |
| Logs→Loki→agent | COSMETIC | 无任何写入者，query_logs 恒空 |
| Monitoring the monitor | COSMETIC | agent/tool-server 无 metrics 无 scrape；Grafana 0 dashboard |
| SLO | DOCUMENTED | 仅文档，0 recording rule |
| Fault injection | FAKE/SIM 为主 | 7 开关：2 FAKE + 4 SIM + 1 REAL(无效量级)；见 FI-02 |
| Chaos Mesh | COSMETIC | YAML 零引用零执行 |
| Docker Compose | E2E VERIFIED | 全栈可启动（.docker_ps2.txt）；web 镜像产物损坏、demo 镜像 root、无 restart/limits |
| Kubernetes | IMPLEMENTED NOT VERIFIED | 8 manifest（RBAC 最小权限/PDB/HPA/NetworkPolicy 真实）；default-deny 疑断 DNS、缺 tool-server Deployment 与数据层、镜像 latest、未实测部署 |
| CI | IMPLEMENTED NOT RUN | Java/Py 测试+7 镜像 build；**lint 未运行、无集成/前端/安全扫描/k8s 校验；workflow 从未触发（0 commit）** |
| Frontend | PARTIAL | vanilla 版可当 Demo 控制台；React 版死代码、Playwright 不可运行 |
| Evaluation | PARTIAL | 200 case/splits/audit 脚手架在；**打分结构性失真（P0-03）** |
| Backup/Restore | IMPLEMENTED | PS1 脚本+文档；**未做恢复演练自动化** |

**结论：没有任何一项达到 PRODUCTION READY。** 达到 TESTED 的仅 Incident 状态机；「E2E VERIFIED」的三项（告警接入、Dashboard、Compose 启动）是真实跑通过的，但均带 P0/P1 缺口。

---

# Production Readiness Scorecard（10 分制，按 Production-like 学生/作品集项目标准）

| 维度 | 得分 | 扣分原因（均有代码证据） |
|---|---|---|
| Architecture | 6 | 组件切分、事件驱动形态、接口抽象（AgentJobProducer/DeduplicationStore/LLMProvider/EmbeddingProvider）正确且可测；扣：MQ 装饰化、tool-server 空壳破坏证据采集故事、双前端、SSE 单实例 |
| Functional Completeness | 5 | 闭环各环节存在且 compose 可跑通；扣：修复是 dry-run 剧场、k8s/db 证据伪造、AM 链路 500、日志证据恒空、Redis 工具是唯一真实数据源 |
| Agent Design | 4 | 循环控制（max_steps=12/15s 超时）、结构化输出、别名归一、注册表校验真实；扣：规则兜底取代推理、工具参数硬编码、Planner 装饰、无 resume、验证非确定性 |
| RAG | 3 | BM25/融合/重排代码真实、runbook 语料 20 篇结构合理；扣：hash 假 embedding、无 chunking、pgvector 未接线、检索评估自证（3 query/4 docs 全 1.0） |
| Evaluation | 2 | 200 case、dev/val/test 划分、泄漏审计脚本的「脚手架意识」好；扣：标签空间不匹配致 0/200、fault_type 泄漏、top3≡top1、baseline 自证、mock 答案污染 |
| Reliability | 3 | 状态机/审计/告警史落库有意识；扣：无任务 claim、无幂等回调、无 crash resume、dedup fail-closed、事务内副作用、MQ 双写不原子 |
| Security | 3 | constant-time 比较、静态 RiskPolicy 立场、K8s RBAC 最小权限、非 root 核心容器；扣：exp 失效、默认口令、回调裸奔、fail-open 风险策略、token len>=8 校验 |
| Observability | 4 | Trace 链路端到端真实、日志带 traceId 的设计正确、CP JVM 指标被采集；扣：Loki 死信箱、3 幻影规则、0 dashboard、self-monitoring 缺位、SLO 无 recording rule |
| Testing | 3 | 真 Docker E2E（3 场景行为断言）存在且曾通过、40+ 真实质量的单测；扣：210/252 Python 用例为生成模板、Java 核心链路 0 测试、假 E2E 进 CI、contract test 校验 mock 自身 |
| Performance | 4 | k6 三脚本+原始日志留档（440/1900 QPS 可信）；扣：QPS 公式错（延迟倒数）、agent benchmark 压 mock、alert 场景阈值击穿未披露、无 p99/资源维度 |
| Docker | 5 | 16 服务 compose 完整可启动、数据层 healthcheck、核心服务非 root、多阶段 CP 构建；扣：web 镜像产物损坏、demo 镜像 root、无 restart 策略/资源限制、无镜像 pin |
| Kubernetes | 4 | manifest 覆盖 RBAC/PDB/HPA/NetworkPolicy/Ingress 且 tool-server RBAC 是真正的最小权限；扣：default-deny 疑断 DNS、缺 tool-server Deployment 与数据层 manifest、latest tag、HPA 与无 claim 消费者组合危险、从未部署验证 |
| CI/CD | 4 | Java/Python 测试+7 镜像 build 真实在 CI 里；扣：lint 装而不跑、无集成测试/前端/安全扫描/k8s 校验、0 commit 从未触发、无缓存、无制品推送 |
| Documentation | 4 | 24 篇覆盖面广、progress.md 准确、验证数字有日志背书；扣：Testcontainers 虚假通过、baseline"100%"误导、架构图领先现实、安全声称过强、测试数三处漂移 |
| Maintainability | 5 | 模块小而清晰、依赖倒置有意识；扣：CP 全模块零日志、魔法字符串状态、死代码群（Runbook/EvaluationCase/TimeoutLLM/mask）、根目录 60+ dot-log 垃圾、双前端漂移 |
| **Overall** | **3.9 / 10** | 形态完整度 ≈7，可信度 ≈2.5；P0 修复后预估可达 6.5+ |

---

# Architecture Findings

1. **组件边界与职责划分合理，无需重构**。Control Plane（有状态编排）/ Agent Runtime（无状态推理）/ Tool Server（副作用网关）/ Demo services（被诊断对象）的四层切分是正确的。接口抽象（`AgentJobProducer` 接口 + RocketMQ 实现 + Noop 实现；`DeduplicationStore` 接口 + Redis/InMemory 双实现）显示作者理解依赖倒置。
2. **MQ 是装饰性组件**（MQ-01/DOC-05）。producer 真实发送到 broker（topic `aisre-agent-task` 已在 `.rocketmq_topics.txt` 验证存在），但 `rocketmq-client-python` 不在 `agent-runtime/requirements.txt`，`mq_consumer.py:15-19` 的 import 必然失败 → `ROCKETMQ_AVAILABLE=False` → **没有任何进程消费 RocketMQ**。事实链路是 `consumer.py` 每 3s HTTP 轮询 `/api/v1/tasks/pending`。架构图（README/docs/architecture.md）把 MQ 画成主链路属于失实。
3. **tool-server 空壳破坏了"证据采集"故事**（TS-01/P0-10）。96 行实现里：`/api/k8s` 返回 `{"dryRun": true}`（从不调 K8s API）、`/api/db` 返回硬编码 `active_connections=42`、`/mcp` 对多数工具 dryRun 回显。Agent 的 k8s/db 证据全部是假的。
4. **Agent 直连观测后端，与文档架构不符**（DOC-04）。`builtin_tools.py` 直连 Prometheus/Loki/Jaeger（compose 注入 URL），但 redis/k8s/db 走 tool-server 且三个 `*_TOOL_URL` 在 compose 中未注入（默认 localhost:8001/8002/8003 → Docker 内必连接失败）。即**默认部署下 redis/k8s/db 工具全部不可用**，而 Loki 又是空的——五类证据里默认部署下真实可用的只有 Prometheus（还查错服务，P0-02）。
5. **前端双轨漂移**（FE-01）。vanilla（可用）与 React+antd（死代码，vite entry 错误、构建产物缺 app.js 必 404）并存且功能漂移。
6. **K8s manifest 形态好但不可部署**（K8S-01）。`network-policy.yaml` 的 default-deny 无 DNS egress 放行，应用后服务发现即断；ingress 引用的 `frontend` Service 无对应 Deployment；tool-server 有 RBAC/PDB 却没有 Deployment；数据层（PG/Redis/MQ/监控栈）无任何 K8s manifest。NEEDS VERIFICATION：整套 manifest 从未实际部署过。
7. **单实例假设遍布**：SSE 内存 emitter、ToolRegistry 进程内限速、TTLCache 进程内、FileIdempotencyStore/FileCheckpointStore 进程内。当前 replicas=1 可用；任何水平扩容前必须先解决（见 Reliability）。

---

# Agent Findings（Agent Runtime）

**总体判断：Multi-Agent 拆分（Planner/Diagnostic/Verification）目前不成立。** Planner 产出物只是工具名列表（`planner.py:8-13` DEFAULT_PLAN 兜底），不做服务/参数规划；Diagnostic 承担全部工作但结论主要来自规则兜底；Verification 是"LLM 猜 RECOVERED"。三者的数据结构（AgentState）稳定可序列化——这是好的，但按当前实现，合成单 Agent + 函数调用不会损失任何能力。

### AR-01 · P0 · 规则兜底诊断 = 答案泄漏 + 默认置信度 0.8 + 伪证据
- **Current State**: `_finalize` 中 LLM 结论为空/unknown 时落入 `_rule_based_diagnosis`；置信度 ≤0 一律改写为 0.8；无证据时追加 `source="rule"` 的伪证据。
- **Evidence**: `agent-runtime/app/agent/diagnostic.py:147-160`（fallback+confidence 改写+伪证据）、`:174-217`（关键词→root cause 映射表："redis" in summary → `redis_connection_pool_exhausted`）。
- **Problem**: 根因不是推理产物而是关键词匹配；`confidence=0.8` 让超时（`diagnosis_timeout`）、unknown、规则兜底全部显示高置信；伪证据让 Evidence 列表永远非空，掩盖"没有证据"这一事实。
- **Why It Matters**: 这是用户点名的"alert 名称 → if/else → Root Cause"反模式本体；同时它使 Evaluation（与 rule 关键词同源）必然虚高，也使技术深挖时整个 Agent 故事坍塌。
- **Failure Scenario**: LLM 挂掉/超时/输出坏 JSON → 系统仍输出 `redis_connection_pool_exhausted, confidence=0.8`，前端与报告展示为高置信结论。
- **Recommended Change**: 规则结果仅作 `fallback_used=true` 标记的 LOW_CONFIDENCE（≤0.3）降级输出；删除 confidence 改写；删除伪证据（无证据就输出空 evidence + status=UNKNOWN）；规则映射如保留，显式命名为 `heuristic_fallback` 并在报告中注明"非 Agent 推理"。
- **Tests Required**: LLM 失败路径断言（rootCause=unknown、confidence≤0.3、evidence 无伪条目）；`diagnosis_timeout` 不获得 0.8 置信度的负向测试。
- **How To Verify**: 关停 LLM 端点跑一次 diagnose，检查响应。
- **Effort**: S · **Dependencies**: 与 P0-03（Evaluation）联动。

### AR-02 · P0 · 工具调用参数硬编码 payment-service + 固定 PromQL
- **Current State**: Diagnostic/Verification 调工具时参数来自 `_tool_arguments`/`_args` 的硬编码字典，与 alert 无关。
- **Evidence**: `diagnostic.py:219-237`（`service: payment-service`，`query: rate(http_server_requests_seconds_count{status=~"5.."}[5m])`）、`verification.py:58-64`（同样硬编码）。
- **Problem**: 对 inventory/order 告警，Prometheus/日志/trace 全部查 payment-service；证据与事件对象错位；Planner 的产出完全不影响工具参数；LLM 全程不提供参数（`tools` 参数从未用于函数调用）。
- **Why It Matters**: 证据链（Metrics/Logs/Trace）从源头失效——这不是 RAG 或 LLM 的问题，是证据采集代码本身写死。
- **Failure Scenario**: inventory-service CPU 告警 → Agent 查 payment 的 5xx 率（正常）→ 证据为空/误导 → 结论由规则兜底给出。
- **Recommended Change**: `_tool_arguments` 从 `state.alert["service"]` 与 incident 上下文构造；Prometheus query 模板按 alertName/fault 类别从 runbook 或配置映射；中期改 LLM function calling 生成参数（openai_compatible 已支持 tools 字段）。
- **Tests Required**: 非 payment 告警的工具调用参数断言（捕获 URL）。
- **Effort**: S · **Dependencies**: 无。

### AR-03 · P0 · 评测结构性失真（并入 P0-03，此处记录 Agent 侧证据）
- **Evidence**: `mock.py:36-45` MockLLM 硬编码 `redis_connection_pool_exhausted` + 三条 evidence（key 与 `evaluation/cases/redis_pool_*.yaml` 的 expected_evidence 完全一致）；`.docker_e2e.log` 显示 cpu/slow_sql 两次真实 E2E 诊断 root_cause 均为 redis pool（错诊）但测试通过（`test_real_faults.py:163-165` 只断言字段存在）。
- **Problem**: 默认演示语义下，Agent 的"诊断正确"是 mock 答案与 rule 关键词的同源命中；真实 E2E 中 2/3 场景错诊未被发现。
- **Recommended Change**: 见 P0-03 与 FI-02。
- **Effort**: — · **Dependencies**: P0-03。

### AR-04 · P1 · LLM 无重试/退避/熔断；Retry 存在但未接线；Timeout 是空壳
- **Evidence**: `llm/base.py:29-39`（TimeoutLLMProvider 注释自认 "In a real HTTP implementation…"，实为透传）；`llm/retry.py:10-25` RetryLLMProvider 仅被测试引用；`main.py:50-58` 构建 provider 未包 retry；`openai_compatible.py:36-38` 单次 POST + raise_for_status，无 429/5xx 处理。
- **Problem**: LLM 抖动直接落 `except Exception` → unknown → 规则兜底（回到 AR-01）。
- **Recommended Change**: `_build_runner` 包 `RetryLLMProvider(OpenAICompatible…, max_retries=3, backoff)`；实现真实 timeout（httpx timeout 已有，删掉空壳 TimeoutLLMProvider 或实现）；429 时读取 Retry-After。
- **Tests Required**: 重试计数测试已存在（test_retry），补接线断言（失败 2 次后成功 → 最终成功且仅 3 次调用）。
- **Effort**: S。

### AR-05 · P1 · 消费幂等与崩溃语义不完整；结果回调 fire-and-forget
- **Evidence**: `consumer.py:51-54,53`（submit 失败仅 `pass`，随后任务仍被 complete → **诊断结果丢失、incident 卡 DIAGNOSING**）；`:66-67,80-81`（mark_processed 在 submit 之后，中间崩溃 → 重复执行）；`idempotency.py:41-45`（write_text 非原子，崩溃可留下损坏文件 → `except: return False` → 重处理）；FileIdempotencyStore 进程内，多副本无效。
- **Problem**: at-least-once 语义下重复执行未防住（与 CP-05 无幂等回调叠加 = 重复 auto-remediation）；提交失败静默丢结果。
- **Recommended Change**: submit 失败时**不**调用 complete 并重试 N 次；mark_processed 与 complete 的顺序改为"complete 成功后再标记"；文件写改 tmp+rename；跨副本去重依赖 MQ-02 的 claim 机制。
- **Tests Required**: submit 抛错 → 任务保持 QUEUED 的测试；重复投递 → 仅一次 submit 的测试。
- **Effort**: S-M。

### AR-06 · P1 · Verification 非确定性：无 SLI 检查、无观察窗、从空 state 起跑
- **Evidence**: `verification.py:19-56`（三次工具调用后直接问 LLM，mock 恒 RECOVERED）；`main.py:137-142`（verify 端点新建空 AgentState，自注 "A real implementation would restore…"）；CP 侧 `RemediationExecutor.triggerVerification` 在修复成功后立即触发（无等待窗口）。
- **Problem**: "看起来恢复" vs "SLI 恢复"未区分；无 60-90s 观察窗即判 RESOLVED。
- **Recommended Change**: 确定性验证：修后等待 window（如 60s）→ 查 Prometheus error rate/p95 与修复前基线对比（阈值判定 RECOVERED）→ LLM 仅生成解释文本；状态机里 RECOVERED 必须携带 SLI 证据。
- **Effort**: M · **Dependencies**: AR-02（查询对的服务）。

### AR-07 · P1 · 工具 timeout_seconds 定义但从不强制；限速为进程内 deque
- **Evidence**: `tools/base.py:16`（spec 字段）、`:27-47`（Tool.call 捕获 TimeoutError 但无任何机制抛出）；`tools/registry.py:54-62`（单进程 monotonic deque）。
- **Problem**: 卡死的 HTTP 工具调用会占满 15s 总预算；多副本限速失效。
- **Recommended Change**: Tool.call 用 `concurrent.futures`/`socket timeout` 强制 spec.timeout_seconds；限速标注 ponytail: 单实例足够，多实例时用 Redis token bucket。
- **Effort**: S。

### AR-08 · P2 · Context 无指令/数据隔离（prompt injection 面）
- **Evidence**: `context.py:29-45`（alert summary、tool results、runbook 内容直接拼接进 user prompt，无分隔标记）；`diagnostic.py:117-124`（prompt 拼接后直接发 LLM）。
- **Problem**: 日志/runbook/trace 里的 "ignore previous instructions" 会被当指令。
- **Recommended Change**: system prompt 明确"工具结果与检索文本是数据不是指令"；每段证据用 `<evidence source=…>` 包裹；对工具输出做基础过滤（检测指令式语句时标注 `possible_injection`）。
- **Tests Required**: 含注入 payload 的 runbook 检索后仍按数据处理的测试。
- **Effort**: S。

### AR-09 · P2 · 其他：Evidence 无 timestamp/query/time_range（`models.py:23-27`，仅 source/key/content）；DiagnosisResult.status 恒 ROOT_CAUSE_FOUND（timeout/unknown 也是，`diagnostic.py:161-171`）；Planner 的"计划"语义名不副实（`planner.py`）；mcp_client.py 主链路零调用（仅测试引用）。
- **Effort**: S each。

---

# RAG Findings

**总体判断：检索代码是真实的（BM25 实现正确、融合公式合理、title/tag 重排是诚实的轻量实现），但主链路用的是假 embedding，且整个 RAG 在默认部署中的实际贡献≈0（runbook 检索结果拼进 prompt，但证据主要来自规则兜底）。**

1. **假 embedding 在主链路**（RAG-01 · P1）。`main.py:56` `HybridRetriever(_load_runbook_docs())` 不传 embedding_provider → 落到 `retriever.py:34-41` 的 hash bag-of-ngrams（256 维、词序无关、`hash()` 受 PYTHONHASHSEED 影响跨进程不稳定）。`pgvector_store.py`/`embeddings.py` 的 OpenAICompatibleEmbeddingProvider 存在但零调用；`agent-runtime/requirements.txt` 无 psycopg/pgvector → **部署镜像内 pgvector 路径根本不可用**；compose 的 postgres:16-alpine 也未装 pgvector 扩展。
2. **无 chunking**（RAG-02 · P2）。`main.py:35-47` 整文件读入为单 Document（20 篇 runbook 全文），长文档检索粒度粗；无 metadata（fault_type/service/tags）参与过滤——Document.tags 字段存在但 `_load_runbook_docs` 不填充。
3. **重排是规则加成**（RAG-03 · P2，可接受）。`retriever.py:136-146` overlap×0.1 加成，注释诚实标注 lightweight。作为"真实 reranker 缺位时的占位"可保留，文档应如实标注。
4. **query rewrite 是关键词规则**（RAG-04 · P2）。`retriever.py:115-125` "connection pool"→"redis pool exhausted"——与 AR-01 同源的泄漏面（评估查询若含这些词会被强化）。
5. **检索评估自证**（RAG-05 · P2）。`run_rag_eval.py`：3 条 query / 4 篇文档，文档内容包含查询关键词 → Recall/MRR 全 1.0。数字无意义。改进：用 200 case 的 summary→对应 runbook（按 fault_type 建 ground truth）在 held-out split 上算 Recall@k/MRR。
6. **检索结果未持久化**（RAG-06 · P3）。`_retrieve_runbook` 只进 context，不落 evidence 表为独立 source=rag 带查询词的记录（当前 evidence content 截断 1000 字符）。

---

# Evaluation Findings

### P0-03 · Evaluation 结构性失真（合并 AR-03/BM-01/DOC-02/T-07）

- **ID**: P0-03
- **Severity**: P0
- **Category**: Evaluation / AI 可信度
- **Current State**: 200 个 case（10 fault × 20 模板近重复）+ dev/val/test 划分（160/20/20）+ 3 个 runner + 审计脚本。runner 真实发 HTTP，但打分链路四处失真。
- **Evidence**:
  - `evaluation/runner/run_evaluation.py:53` — summary=`f"{service} {fault_type}"`，**fault_type（即答案标签）直接进入告警输入**；与 `diagnostic.py:174-217` 规则兜底（对 summary 关键词映射）同源 → 答案泄漏进输入。
  - `run_evaluation.py:88-95` — 匹配用 `expected in root_cause or root_cause in expected` 双向子串 + 小写化；**标签空间不匹配**：期望是自然语言（"Redis connection pool is exhausted causing payment timeouts"），agent 输出 snake_case（`redis_connection_pool_exhausted`）→ 主审计离线模拟打分结果 **0/200**（已实测运行模拟脚本）。
  - `run_evaluation.py:75-95` — top3 与 top1 用同一次判断，top3≡top1。
  - `run_evaluation.py:97-98,116` — tokens 恒 0、recovery_success_rate 硬编码 0.0。
  - `run_baseline.py:27-35,34-70,87-96` — 3 个手写 case；"LLM"=自写关键词映射 EvidenceAwareLLM；final 组把含答案的文本作为 tool_hint 注入 → 0%/33.3%/100% 为程序写死的自证结论（实测复现一致）。
  - `evaluation/splits/*.json` — 存在但 run_evaluation 不读 splits（grep 零引用）→ dev/test 无区分、20 模板近重复跨 split 泄漏。
  - `audit_evaluation.py` — 只检查 root_cause==fault_type 的精确泄漏，未覆盖 summary 含 fault_type 的路径。
  - `docs/benchmark.md:55-66` 把 baseline 表作为核心对比引用；docs 声称 "No numbers are fabricated"（PARTIAL：数字真实来自脚本，但脚本自证）。
- **Problem**: 当前**不存在任何可信的准确率数字**；数据集存在输入泄漏、近重复、split 未用三类问题；baseline 无法证明 RAG/Trace/Agent 的增量价值。
- **Why It Matters**: Evaluation 是项目"AI 能力可信"的唯一凭证；现状在技术深挖（"你的 100% 怎么来的"）时一问即穿。
- **Failure Scenario**: 评审人要求现场重跑 run_evaluation → 输出 0.0 accuracy；或追问 fault_type 与规则兜底关系 → 承认泄漏。
- **Recommended Change**（按顺序）:
  1. 定义 canonical RCA 标签空间（snake_case 枚举，与 case 的 `expected_root_cause_label` 对齐；现自然语言句子保留为 description）。
  2. runner 输入剔除 fault_type：summary 用模板化中性描述（如 "payment-service 上游依赖超时"），保留 service/severity/alertName；把 `alertName` 从 fault_type 改为通用告警名（latency_high/error_rate_high 等无答案语义的名称）。
  3. 匹配逻辑：Top-1 精确标签匹配；Top-3 基于真实 ranked list（DiagnosisResult 需输出候选列表，或对 confidence 排序的多次采样）；去掉双向子串。
  4. run_evaluation 读 splits；报告按 dev/validation/test 分别输出并落盘 `evaluation/results/<date>.json`。
  5. baseline 重做：真实 LLM（openai provider）+ 同一打分；如保留离线 baseline，文档标注"3-case 示意，非能力测量"。
  6. 增加指标：Unknown Rate、Evidence Precision/Recall（对照 expected_evidence）、tool 成功率、平均/ P95 时延、token 用量（openai provider 返回 usage）。
- **Tests Required**: 打分器单测（构造已知输出→期望分数）；泄漏回归测试（summary 不得包含 fault_type 子串）。
- **How To Verify**: 修复后 `python evaluation/runner/run_evaluation.py` 在 test split 上产出非 0 且非 1 的可信数字，并附结果 JSON。
- **Estimated Effort**: M（2-3 天）
- **Dependencies**: AR-01（规则兜底降级后分数才有意义）、AR-02（证据对服务）。

**其余 Evaluation/数据集 findings**：
- EV-01 (P2)：10 fault × 20 同模板近重复 → 攻击面单一；建议每 fault 至少 5 种表述模板 + 服务/严重度扰动，防止模板记忆（在 canonical 标签修复后做）。
- EV-02 (P3)：`hash(case["id"])` 作 incident_id 受 PYTHONHASHSEED 影响非确定（`run_evaluation.py:48`）。

---

# Backend Findings（Control Plane / DB / Redis）

Control Plane 全量 findings 见子审计（CP-01~CP-25），此处汇总关键项并补 DB/Redis：

**正确性/一致性（P0/P1）**：审批参数脱钩+未知动作兜底 restart_pod（CP-01）、RiskPolicy fail-open（CP-02）、JWT exp 永不生效（CP-03）、默认凭据 admin/admin（CP-04）、agent 回调裸奔+saveDiagnosis 无幂等（CP-05）——均入 P0。MQ 双写不原子（CP-07）、幂等键含 UUID 失效+任务生命周期断头（CP-08）、LIKE 错绑+并发重复 incident（CP-09）、无乐观锁+状态机 bypass（CP-10）、事务内 HTTP 副作用（CP-11）、审批无过期/REJECT 悬挂/decidedBy 可伪造（CP-12）。

**数据库**：
- Flyway V1/V2 真实存在且 schema 完整（10 表+索引+幂等唯一索引）——**好**。
- `application.yml:10` `ddl-auto: update` 与 Flyway 并存，实体与 SQL 已漂移（rawBody/report/argumentsJson 长度 4096 vs TEXT；idempotency_key 唯一索引仅在 SQL）（CP-17 · P1）。
- 无 @Version（全部 11 实体）；无 DB 层防双 incident 约束（CP-10/CP-09）。
- 性能：`IncidentService.list` findAll+内存排序、`AlertService.findActiveIncident` 全量 LIKE、`DashboardController` findAll 统计（CP-20 · P2）。**EXPLAIN 未执行**（审计只读约束 + 未起 DB），NEEDS VERIFICATION：以当前数据量推断均走 seq scan，incident 表无界增长后 dashboard 变慢。
- 无限增长表：alert（每条告警落库）、audit_log、evidence、tool_call——无分区/归档策略（P3，量大后处理）。
- N+1：未发现明显 N+1（detail API 用 repository 派生查询按 incidentId 取，可接受）。

**Redis**：
- 用途：仅 dedup（`aisre:dedup:` 前缀 SETNX EX 5min）。agent 侧 TTLCache 是进程内的，未用 Redis。
- **fail 行为：fail-closed**——`RedisDeduplicationStore.setIfAbsent` 无 try/catch（CP-15），Redis 挂 → `AlertService.ingest` 抛异常 → 告警入口 500，Alertmanager 重试耗尽后告警丢失。**同时 dedup 结果不 gate 任何写入**（重复告警照常落库计数），语义双重混乱。
- InMemoryDeduplicationStore 存在但无自动降级装配（仅测试用）。

**Redis 挂掉时全系统行为**（回答审计问题）：告警接入 500（入口不可用）；其余（incident 查询、诊断、审批）不依赖 Redis，可用。改进：dedup 异常时降级放行（fail-open）+ WARN + 指标，同时 DB fingerprint 兜底去重。

---

# Reliability Findings（MQ / 分布式任务 / 恢复）

### MQ-01 · P1 · RocketMQ 消费端从未启用，真实链路是 HTTP 轮询
- **Evidence**: `agent-runtime/requirements.txt`（无 rocketmq 客户端）；`mq_consumer.py:15-19`（import 失败 → ROCKETMQ_AVAILABLE=False）；`.rocketmq_test.log`（`ImportError: rocketmq dynamic library not found`）；`main.py:61-66`（只启动 consumer_loop 轮询）；`docs/ADR-0001` 与 implemented-features.md 已诚实标注未验证。
- **Problem/Impact**: broker 里消息无人消费（积压）；「RocketMQ 支持」的等级是 PARTIAL；两套消费路径并存但只有一条活着。
- **Recommended Change**: 二选一——(a) 承认现状：删 mq_consumer.py 或标注 experimental，架构图改轮询；(b) 真启用：换 rocketmq-client-python 为可安装的客户端（如 rocketmq-python-client 5.x / HTTP proxy 模式）并在 compose 验证端到端。**对项目定位，(a)+(b) 都可接受，但不许再让文档领先现实。**
- **Effort**: S(a)/L(b)。

### MQ-02 · P1 · 任务无 claim/lease：多副本必然重复执行
- **Evidence**: `AgentTaskController.java:24-27`（GET pending 返回全部 QUEUED，无领取语义）；`consumer.py:57-85`（取→诊断→complete，无租约）；K8s `agent-runtime.yaml` HPA maxReplicas=5；FileIdempotencyStore 进程内。
- **Problem**: 两个副本同时 GET → 同一 incident 双诊断 → CP saveDiagnosis 无幂等（CP-05）→ 双份 evidence/审批/**双次 auto-remediation 执行**。
- **Recommended Change**: claim 机制（最小实现：`UPDATE agent_task SET status='RUNNING', claimed_by=?, claimed_at=? WHERE status='QUEUED'` 条件更新抢租约 + 超时回收扫描）；消费端带 taskId 上报，saveDiagnosis 按 (incidentId, taskId) 幂等。
- **Tests Required**: 两消费者并发领取同一任务仅一成功的集成测试。
- **Effort**: M。

### MQ-03 · P1 · ACK 时机/毒消息/重复投递语义
- **Evidence**: `mq_consumer.py:28-41`（若启用：handler 成功后才 CONSUME_SUCCESS；任何异常 → RECONSUME_LATER 无限重试，无最大重试/DLQ 处理代码）；idempotency 标记在 handler 后（非原子）；producer 侧eventId 每次 UUID（CP-08）。
- **Problem（回答审计问题）**: Agent Runtime 宕机 → 未 ACK 消息由 broker 重投（好）；处理到一半 crash → 重投后靠 idempotency，但文件存储进程内+非原子 → 会重复；消息长期失败 → 无 DLQ 消费/告警（broker 侧 %DLQ% 默认存在但无人看）。
- **Recommended Change**: 启用 MQ 时同步实现：eventId 幂等键（DB 存储而非文件）、最大重试后入 DLQ + 告警（复用 CP 的告警入口自省）。
- **Effort**: M · **Dependencies**: MQ-01。

### 其他 Reliability：
- **Crash recovery**（P0-09/T-03）：checkpoint 仅 run 完成后 save（`runner.py:35-44`），`load` 生产零调用（grep 证实），verify 从空 state 起（`main.py:140` 自注）。真实现 = 原子写 + diagnose 入口先 load + kill-restart 集成测试；或改名 "checkpoint persistence" 并修正文档。**CP 进程重启**：状态全在 PG，天然恢复 ✓；**tool-server/Redis/MQ/PG 重启**：tool-server 无状态 ✓，Redis 挂→告警 500（CP-15），MQ 挂→告警 500（CP-07 producer 在事务内），PG 挂→整体不可用（合理）。
- **EXECUTING 卡死**：RemediationAction 状态 EXECUTING 无超时扫描恢复（进程崩溃在 HTTP 中途则该行永久 EXECUTING）(P2，随 R-M 重构处理)。
- **审批并发竞态**（CP-06）、**SSE 无心跳**（CP-19）、**健康检查不查依赖**（CP-21）。

---

# Security Findings

### P0-04 · 审批→执行链路失效（合并 CP-01 + CP-02 + CP-13 + SEC-01 + tool-server token 部分）

- **Current State**: 审批闸门在四处同时失效：① payload 恒 `{}`，执行 URL 全硬编码（`default/default`、replicas=3）；② 未知/拼错动作兜底 restart_pod；③ RiskPolicy 未知动作默认 LOW_RISK → 自动审批立即执行；④ execution token：auto-approval 走 fallback `change-me-in-production`、tool-server 只校验 `len(token)>=8`、token 走 URL query。
- **Evidence**: `AgentResultService.java:124-131,122-144`、`RemediationExecutor.java:104-118,107-108,34`、`RiskPolicy.java:39`、`tool-server/app.py:80-84,86`。
- **Failure Scenario**: LLM 幻觉动作 `restart_all_pods_now` → LOW_RISK → auto-APPROVED → buildUrl default → restart_pod default/default；人工审批"scale payment-service" → 实际 scale default/default。
- **Recommended Change**: actionPayload 存真实参数并驱动 URL；未知动作 fail-closed（记 FAILED+审计）；RiskPolicy 默认 HIGH_RISK；token 放 header 且与签发记录绑定（HMAC 或回查）；删除 default 兜底分支。
- **Tests Required**: 幻觉动作不执行；审批参数与执行参数一致；错 token 401。**Effort**: M。

### P0-05 · Agent 回调裸奔 + 无幂等（CP-05）
- **Evidence**: `AuthInterceptor.java:26`；`AgentResultService.saveDiagnosis` 无幂等/无来源校验；重放即重复新建审批并重复执行低风险修复。
- **Recommended Change**: agent 专用 token（header）+ (incidentId, taskId) 幂等键 + 仅允许从 DIAGNOSING 推进一次；重放返回原结果。
- **Effort**: M。

### P0-06 · 认证失效三件套（CP-03 + CP-04）
- **Evidence**: `AuthService.java:26,45-46`（exp 为数字、extract 找带引号模式 → 永远 null → 过期检查永不执行）；`:19` 默认密钥；`AuthController.java:26-31,44-49`（admin/admin 明文 equals，compose/k8s 均未覆盖）。
- **Recommended Change**: Jackson 解析取 Long exp；启动校验 secret 非默认 ≥32B、口令已注入（否则 fail-fast）；BCrypt；登录失败限速。
- **Effort**: S-M。

### P1 安全项：CP-14（AuthZ 矩阵过宽：全部 GET/actuator/tasks complete/alerts 无 webhook secret）、CP-12（审批无过期/decidedBy 可伪造）、AR-08（prompt injection 面）、DOC-11（.env 真实 API key，未入库；轮换+scan-secrets 接 CI）、FI 系（告警注入伪造）。

**攻击面小结**（当前可被匿名利用的最短链）：匿名 `POST /api/v1/alerts`（无 secret）→ 匿名 `POST /incidents/{id}/diagnosis` 塞伪 rootCause+低风险 recommendedActions → auto-approval → RemediationExecutor GET（token 仅长度校验）→ tool-server dryRun。当前实际危害被 tool-server 的 dryRun 假实现"意外地"限制了——这是**用 bug 掩盖漏洞**，P0-04/10 修复后安全层必须同步修，否则风险升级。

**Prompt Injection（AR-08）**：runbook/log/trace 内容无指令/数据隔离，NEEDS VERIFICATION（无注入测试存在）。

---

# Observability Findings

**真实可用的**：Trace 全链路（demo OTLP→collector→Jaeger、W3C 传播、resource 正确）——全项目最佳部分；CP 暴露 `/actuator/prometheus` 且被 scrape；demo 指标（`http_requests_total`/`http_request_duration_seconds`）与 3 条规则匹配。

**关键缺口**：
1. **FI-01 (P0)**：AM→CP webhook 契约断裂（`AlertRequest` 扁平 record vs AM 嵌套 payload；service NOT NULL → ingest 500；NEEDS VERIFICATION: 实际 500 vs null 塌缩）。正式链路 Metric→Rule→AM **在最后一环断掉**，所有测试/压测直连 POST /alerts。
2. **FI-04 (P1)**：Loki 零写入者（无 promtail、无 loki driver、collector 无 logs pipeline）→ `query_logs` 恒空 → 日志证据恒缺，traceId 关联日志的设计（`observability.py:70`）落空。
3. **FI-05 (P1)**：Prometheus 未开 `--web.enable-remote-write-receiver`，collector metrics 导出 404；且 demo 无 OTel MeterProvider，双向空转。
4. **FI-06 (P1)**：3 条规则引用幻影 metric（redis_connected_clients/db_active_connections/rocketmq_consumer_lag，无 exporter）；cpu_saturation 故障是 sleep → HighCPU 永不触发（FI-03）。
5. **FI-08 (P2)**：monitoring the monitor 缺位：agent-runtime/tool-server 无 /metrics 无 scrape；Grafana 0 dashboard；监控栈自身不在 `up` 规则内；AI SRE 自身指标（诊断时延、tool 失败率、队列深度、DB 池）**一项都没有**。
6. **FI-09 (P2)**：SLO 仅文档，0 recording rule，无 error budget/burn-rate。
7. **FI-11 (P3)**：无 redis span、access log 无 traceId、X-Request-Id 恒 "-"。
8. **可观测的事件缺口**：Agent/Tool/LLM 层无任何 metrics（时延、token、失败率）；Remediation 成功率、Verification 通过率无指标。

---

# Testing Findings

测试金字塔（实测数字）：

| 层 | 数量 | 质量 |
|---|---|---|
| Java 单测 | 8 用例/3 类 | 合格但窄（JWT/状态机/InMemory dedup）；核心链路 0 覆盖 |
| Java 集成 | 1 用例 | 仅断言容器启动；CI 不跑；**9 份日志全 BUILD FAILURE** |
| Python 单测 | 252 方法（实测 run: 249+1 skip） | 210 个为生成重复模板（test_extended.py）；~42 个质量合格 |
| Contract | 5 用例 | 校验 mock 自身（假 contract） |
| Fake E2E | 3+1 场景 | mock server 硬编码答案；进 CI 作为"E2E 通过"依据 |
| 真 E2E (Docker) | 3 场景 | 唯一真闭环，曾通过（.docker_e2e.log）；**CI 永远 skip（RUN_E2E gate）**；2/3 场景错诊未被发现 |
| 浏览器 E2E | 2 用例 | 不可运行（依赖缺、断言目标错位） |
| 压测 | k6×3 + py×3 | 有原始日志；公式/口径问题（BM-03） |
| Evaluation | 200 case | 结构性失真（P0-03） |

**要点**：测试数量与风险倒挂——审批/修复/鉴权矩阵这些最高危链路 0 测试（CP-24/T-02）；`test_crash_recovery.py` 测的是 save/load roundtrip（T-03/P0-09）；`run_all_local_tests.py` 把同一套 unittest 跑两遍且不含 Java。

---

# Performance Findings

- **可信数字**（有原始日志）：alert ingestion 440 QPS @ P95 682.88ms（**超出脚本自设 500ms 阈值，k6 以错误退出——文档未披露**）；incident query 1900 QPS @ P95 4.42ms；Docker E2E 全链路 ~4.2s。
- **不可信/口径错**：`local_api_load_runner.py:44-49` qps=n/sum(latencies)（延迟倒数当吞吐，并发 10 低估 ~10×）；agent benchmark 2.047s 压的是 mock server；数字无结果文件留存。
- **缺失维度**：无 p99、无 CPU/内存/DB 连接池/Redis 连接/MQ lag 采集（相关 exporter 缺失）、无诊断时延 P95 的真实 LLM 测量（tokens 恒 0）、无 Agent 并发能力测试。
- **已知结构性开销**：诊断内置 15s 预算 + LLM 每步串行；修复执行同步 HTTP 30s 阻塞审批事务（CP-11）。

---

# Docker Findings

- compose 16 服务完整、数据层 healthcheck 齐全、CP/AR/TS 三镜像非 root、CP 多阶段构建、agent-runtime 构建包含 knowledge-base。`.docker_ps2.txt` 证实全栈曾 Up（postgres/redis/namesrv healthy）→ **全新机器 `docker compose up -d` 大概率可用**（NEEDS VERIFICATION：仅 tool-server `*_TOOL_URL` 未注入导致 redis/k8s/db 工具必失败，DOC-04）。
- 缺口：全 compose **无 restart policy**、无资源限制；demo 服务镜像 root 运行；web 镜像构建产物损坏（FE-01）；CP Dockerfile `COPY . .` + `mvn -Pdocker -DskipTests`（测试不在构建里、无依赖缓存层）；无镜像 pin（除基础镜像 tag 外无 digest）；Grafana admin/admin。
- 垃圾：仓库根 60+ `.docker_*.log`/`.k6_*.log` 等调试产物未 ignore、未归档（GIT-02）。

---

# Kubernetes Findings

- 真实存在的优点：`tool-server-rbac.yaml` 是真正的最小权限 Role（pods/services/events get/list/watch + deployments patch）而非 cluster-admin（用户点名的 CRITICAL 不存在）；PDB/HPA/NetworkPolicy/Ingress/namespace 齐全；secret 用 secretKeyRef。
- 缺口：① `network-policy.yaml` default-deny 无 DNS egress → 应用后 DNS 解析断（NEEDS VERIFICATION，需实测）；② 无 tool-server Deployment/Service（有 RBAC/PDB 无负载）；③ ingress 引用 frontend Service 但无 frontend Deployment；④ 数据层+监控栈无 K8s manifest（postgres/redis/rocketmq/prometheus…），"K8s 部署"只覆盖应用层；⑤ 全部镜像 `:latest`；⑥ 多数无 liveness、无 securityContext（runAsNonRoot/fsGroup）；⑦ HPA(agent-runtime max 5) 与无 claim 消费者组合 → 重复执行（MQ-02）；⑧ k8s 路径无 OTEL env（trace 断）、`LLM_PROVIDER=mock` 硬编码；⑨ jwt.secret/admin.password 未注入 K8s（P0-06 在 K8s 同样生效）。
- 判级：IMPLEMENTED BUT NOT VERIFIED（从未有部署证据）。

---

# Frontend Findings

- **vanilla 版（实际部署）可当 Demo 控制台**：列表+统计、详情八段（信息/时间线/Agent 步骤/Evidence/ToolCall/修复/审计/审批）、审批决策（带 token）、Report、loading/empty/error 三态。✔
- **React+antd 版是死代码**（FE-01 · P1）：vite entry 指向 vanilla index.html；`index.react.html` 无构建/部署路径引用；实测 vite build 产物缺 app.js（必 404）；compose 挂载源码目录绕过镜像；"React 构建已通过"的证据是 344B context 的缓存日志。
- 语义缺口（FE-03 · P2）：`window.prompt()` 登录；无 401 拦截/过期处理；vanilla SSE `onerror→close` 主动断连不重连；React 无 error 态。
- Playwright（FE-02 · P2）：依赖不在 lock、CI 无 job、断言文本只存在于 React 版 → 从未可运行。
- 判定：**能作为完整 AI SRE Demo 控制台（vanilla）**；需定版双轨并补 401/重连。

---

# Documentation Findings

总表见文档子审计。最重要的不实/过时点（DOC-01~DOC-12）：

1. **DOC-01 (P0)** Testcontainers "BUILD SUCCESS/通过" = FALSE（9/9 日志 BUILD FAILURE，4 份文档宣称通过）。
2. **DOC-02/DOC-03 (P0)** Evaluation "Final 100%" 为 3-case 自证；Mock LLM 恒答 redis（.docker_e2e.log 三场景全 redis，2/3 错诊）被当能力证明。
3. **DOC-04/DOC-05 (P1)** 架构图工具链路失实（三工具 URL 未注入必失败）；MQ 主链路是画的。
4. **DOC-06 (P1)** security.md 过强（"一次性"token 无回收；tool-server len>=8；GET 全开放；脱敏死代码）。
5. **DOC-07 (P1)** production-readiness-audit.md 整体过时（方向为低估）。
6. **DOC-08~DOC-10 (P2)** 测试数 222/233/240/静态264 四处漂移；k6 阈值击穿未披露；README Future Work 与现状矛盾；limitations.md 自相矛盾。
7. **正面**：progress.md 是最准确文档；验证数字（k6/E2E/pgvector/topic）有日志背书；remaining-requirements.md 诚实；文档"无中生有"很少，主要问题是"把演示当验证"。

---

# 高级感 vs 真实性对照（关键技术点名）

| 技术点 | 判级 | 一句话事实 |
|---|---|---|
| Multi-Agent (Planner/Diagnostic/Verification) | **PARTIAL** | 三类存在、结构稳定；但 Planner 装饰、Verification 空转、Diagnostic 结论主要来自规则兜底 |
| MCP | **COSMETIC** | 手写 JSON-RPC 端点；主链路零调用；多数工具 dryRun 回显 |
| Tool Calling / Tool Registry | **PARTIAL** | 注册表/Schema 校验/限速/权限位真实；但 LLM 不生成参数（硬编码）、超时不强制、k8s/db 数据假 |
| Hybrid RAG (BM25+Vector+Rerank) | **PARTIAL** | 代码真实、公式合理；假 embedding、无 chunking、pgvector 未接线、评估自证 |
| Checkpoint / Crash Recovery | **COSMETIC** | 仅 run 后 save；load 生产零调用；无原子写；"recovery 测试"是 roundtrip |
| RocketMQ | **PARTIAL** | producer 真实 + topic 存在 + broker 部署；consumer 依赖缺失从未消费；事实链路 HTTP 轮询 |
| Idempotency | **COSMETIC** | 幂等键含 UUID 永不重复；token 校验 len>=8；文件存储进程内非原子 |
| Auto Remediation | **COSMETIC** | 审批后 GET 硬编码 URL → tool-server dryRun:true；"修复"无真实副作用 |
| Kubernetes | **PARTIAL** | manifest 真实且 RBAC 最小权限；但 default-deny 疑断、缺关键负载、从未部署验证 |
| Chaos Engineering | **COSMETIC** | 3 个 Chaos Mesh YAML 零引用零执行 |
| Evaluation | **PARTIAL** | 脚手架真实（200 case/splits/审计脚本）；打分结构性失真 |
| OpenTelemetry 分布式追踪 | **REAL** | OTLP→collector→Jaeger + W3C 传播，端到端真实可用 |
| Prometheus 告警规则 | **PARTIAL** | 8 条中 3 条可触发、3 条幻影 metric、AM→CP 契约断裂 |
| Flyway 迁移 | **REAL**（被 ddl-auto 稀释） | V1/V2 真实且 schema 完整 |
| JWT/RBAC | **PARTIAL** | 签名/常时比较真实；exp 永不生效、默认凭据、矩阵过宽 |
| SSE | **PARTIAL** | 单实例可用；无心跳/重放/多实例 |
| Docker Compose | **REAL** | 16 服务可启动，全栈验证过 |
| 真实故障注入 | **FAKE/SIM** | 7 开关中无一真实制造资源耗尽 |

---

# Top 5 Strengths / Top 5 Weaknesses

**Strengths（来自代码事实）**
1. 端到端闭环形态真实存在且 compose 全栈可启动（告警→去重→Incident→任务→诊断→证据→审批→修复→验证→报告→审计），schema（Flyway V1/V2）与审计埋点完整。
2. 分布式追踪端到端真实（OTLP→Jaeger + W3C 传播）——唯一"全过程真"的观测段，且日志格式带 traceId 的设计正确。
3. 接口抽象与可测性意识：AgentJobProducer/DeduplicationStore/LLMProvider/EmbeddingProvider 依赖倒置；状态机纯函数+单测；constant-time JWT 比较；告警原始数据全量落库可追溯。
4. 真 Docker E2E（3 故障场景、行为断言）存在且曾通过；k6 有原始日志留档——验证习惯在线。
5. Evaluation 脚手架意识：200 case、dev/val/test 划分、泄漏审计脚本、RAG 指标脚本——修好打分链路后是现成的可信评测底座。

**Weaknesses（来自代码事实）**
1. AI 证据链大面积虚假/断链：规则兜底冒充推理 + 工具参数硬编码 + tool-server 假数据 + Loki 空转（P0-01/02/10、FI-04）。
2. Evaluation 结构性失真且自证（P0-03）：当前没有可信准确率数字。
3. 审批/执行/幂等/claim 的可靠性语义缺失：重放/多副本/幻觉动作均可重复或绕过执行（P0-04/05、CP-06/08、MQ-02）。
4. 安全默认值全面反向：exp 失效、admin/admin、fail-open 风险策略、GET 全开放（P0-06、CP-02/14）。
5. 工程卫生：0 git commit、CI 从未触发、双前端死代码、零日志 CP、根目录 60+ 调试产物、文档三处虚报（GIT-01/02、CI-03、DOC-01/08）。

---

# P0 Issues（完整格式）

### P0-01
- **ID**: P0-01（源 AR-01）
- **Severity**: P0
- **Category**: Agent / RCA 真实性
- **Current State**: LLM 结论为空/unknown/超时/坏 JSON 时落入关键词规则兜底；confidence ≤0 一律改写 0.8；无证据时伪造 rule 证据。
- **Evidence**: `agent-runtime/app/agent/diagnostic.py:147-160, 174-217, 50-58`（timeout 也走 _finalize 拿 0.8）。
- **Problem**: RCA 非推理产物；置信度与证据被系统性美化；timeout/unknown 与真诊断不可区分。
- **Why It Matters**: "Evidence-Driven RCA" 的核心主张不成立；Evaluation 与文档的可信度连带崩塌。
- **Failure Scenario**: LLM 端点宕机 → 仍输出 `redis_connection_pool_exhausted, 0.8` 高置信结论。
- **Recommended Change**: 兜底输出 rootCause=heuristic 候选 + confidence≤0.3 + `fallbackUsed=true`；删 confidence 改写与伪证据；unknown 保持 unknown。
- **Implementation Direction**: `_finalize` 重写（~30 行 diff）；DiagnosisResult 增加 `fallbackUsed` 字段并透传到 CP。
- **Tests Required**: LLM 异常/超时/坏 JSON 三路径断言。
- **How To Verify**: 手动 mock LLM 抛错跑 diagnose，检查响应 JSON。
- **Estimated Effort**: S
- **Dependencies**: P0-03。

### P0-02
- **ID**: P0-02（源 AR-02）
- **Severity**: P0
- **Category**: Agent / 证据采集
- **Current State**: 工具参数硬编码 payment-service 与固定 PromQL，与 alert/incident 无关；Planner 产出不影响参数。
- **Evidence**: `diagnostic.py:219-237`、`verification.py:58-64`。
- **Problem**: 非 payment 告警的证据查错对象；证据链源头失效。
- **Why It Matters**: 对"某服务 CPU 高"的告警查另一个服务的 5xx 率，证据为空或误导。
- **Failure Scenario**: inventory cpu_saturation → 查 payment 5xx（正常）→ 无证据 → 规则兜底定论。
- **Recommended Change**: `_tool_arguments(alert)` 按 alert.service/alertName 生成；中期 LLM function calling。
- **Tests Required**: 非 payment 告警断言工具 URL 中 service。
- **Estimated Effort**: S
- **Dependencies**: 无。

### P0-03
- **ID**: P0-03（源 AR-03 + BM-01 + DOC-02 + DOC-03 + T-07）
- **Severity**: P0
- **Category**: Evaluation
- **Current State / Evidence / Problem / Recommended Change / Tests / Effort**: 见 Evaluation Findings 的 P0-03 完整条目（标签空间不匹配 → 实测 0/200；fault_type 泄漏进输入；top3≡top1；baseline 3-case 自证；mock 答案污染；splits 未用）。
- **Estimated Effort**: M（2-3 天）
- **Dependencies**: P0-01、P0-02。

### P0-04
- **ID**: P0-04（源 CP-01 + CP-02 + CP-13 + SEC-01）
- **Severity**: P0
- **Category**: Security / Remediation
- **Current State**: 审批与执行参数脱钩（payload 恒 `{}`，URL 硬编码 default/default/replicas=3）；未知动作兜底 restart_pod；RiskPolicy fail-open（未知→LOW_RISK→auto-execute）；execution token 走 URL、对端仅校验长度 ≥8、fallback token 与 compose 注入值不一致。
- **Evidence**: `AgentResultService.java:124-131,122-144`、`RemediationExecutor.java:104-118,34,107-108`、`RiskPolicy.java:39`、`tool-server/app.py:80-84`。
- **Problem**: 审批闸门与实际生产动作无绑定；幻觉/拼错动作自动执行。
- **Why It Matters**: 人工审批失去意义；与 P0-05 组合后，任何能访问 CP 的匿名方都能驱动"修复"。
- **Failure Scenario**: LLM 幻觉 `restart_all_pods_now` → auto-APPROVED → restart_pod default/default。
- **Recommended Change**: actionPayload 真实参数化（namespace/deployment/pod/replicas 从 incident.service 推导）；fail-closed 默认；删 default 兜底；token header 化 + 绑定校验。
- **Tests Required**: 幻觉动作不执行；审批↔执行参数一致性；token 校验契约测试。
- **Estimated Effort**: M
- **Dependencies**: P0-05（幂等）协同。

### P0-05
- **ID**: P0-05（源 CP-05 + AR-05 部分）
- **Severity**: P0
- **Category**: Security / Reliability
- **Current State**: agent 回调（diagnosis/verification/remediations）与 tasks/complete 免鉴权；saveDiagnosis 无幂等键、无来源校验，每次调用新建审批并对低风险动作立即执行。
- **Evidence**: `AuthInterceptor.java:23-35`、`AgentTaskController.java:29-36`、`AgentResultService.java:64-155`。
- **Problem**: 重放/伪造/多副本竞争 → 重复证据、重复审批、重复修复执行；匿名可伪造 verification=RECOVERED 推 RESOLVED。
- **Why It Matters**: at-least-once 消息 + 重试 + K8s 多副本的组合下重复执行是必然事件，不是理论风险。
- **Failure Scenario**: agent 超时重试 POST diagnosis ×3 → restart_pod 执行 3 次。
- **Recommended Change**: agent 专用 token；(incidentId, taskId) 幂等键（重复提交返回原结果）；仅允许 DIAGNOSING→ROOT_CAUSE_FOUND 推进一次。
- **Tests Required**: 重放幂等测试；无 token 401；伪造 verification 状态机负向测试。
- **Estimated Effort**: M
- **Dependencies**: MQ-02（taskId 需可靠传递）。

### P0-06
- **ID**: P0-06（源 CP-03 + CP-04）
- **Severity**: P0
- **Category**: Security
- **Current State**: JWT exp 校验永不生效（解析 bug）；默认签名密钥；admin/admin 明文口令；compose/K8s 均未注入覆盖。
- **Evidence**: `AuthService.java:19,26,45-46`、`AuthController.java:26-31,44-49`、`docker-compose.yml`（control-plane env）、`deploy/k8s/control-plane.yaml`。
- **Problem**: 令牌永久有效 + 弱默认凭据 + 8080 对外 → 审批接口可被完全接管。
- **Failure Scenario**: 一年前 token 仍可 approve。
- **Recommended Change**: Jackson 解析 Long exp；启动 fail-fast 校验 secret/口令非默认；BCrypt；失败限速。
- **Tests Required**: 过期 token 必拒；默认凭据启动失败。
- **Estimated Effort**: S-M
- **Dependencies**: 无。

### P0-07
- **ID**: P0-07（源 FI-01）
- **Severity**: P0
- **Category**: Observability / 正式告警链路
- **Current State**: Alertmanager webhook payload（嵌套 alerts[].labels/annotations）与扁平 `AlertRequest` 不匹配 → 字段全 null；`incident.service` NOT NULL → ingest 抛数据完整性异常 → 500（Alertmanager 重试耗尽后告警丢失）。NEEDS VERIFICATION：实测响应码（500 vs 202+null 塌缩，取决于运行时约束与 dedup 先后）。
- **Evidence**: `control-plane/.../dto/AlertRequest.java:5-12`、`alertmanager.yml:9-12`、`AlertService.java:32-33`、`V1__initial_schema.sql`（service NOT NULL）。
- **Problem**: Metric→Rule→AM→CP 的正式链路在最后一环断掉；所有测试/压测均直连 POST /alerts。
- **Why It Matters**: 项目叙事的起点（"从真实告警开始"）依赖这条链路；演示时用 Prom 触发故障会在评委面前直接翻车。
- **Recommended Change**: 新增 `/api/v1/alerts/alertmanager` 适配端点（DTO 从 labels/annotations 提取 service/alertName/severity/summary/resource；AlertRequest 保留给测试）或双 DTO；补一条走全链路的 E2E（Prom 触发→AM→CP→Agent）。
- **Tests Required**: AM 真实 payload 样例的 202 断言 + dedup 按 label 正确去重。
- **Estimated Effort**: M
- **Dependencies**: 无。

### P0-08
- **ID**: P0-08（源 FI-02）
- **Severity**: P0
- **Category**: Fault Injection
- **Current State**: 7 个可注入故障：redis_pool_exhausted/thread_pool_exhausted = FAKE（log+503）；redis_slow_command/slow_sql（无 DB！）/cpu_saturation（sleep）/downstream_timeout = SIM；memory_pressure = 30MB 瞬时（阈值 500MB）。
- **Evidence**: `payment-service/app.py:67-72,73-75`、`inventory-service/app.py:61-66`、`order-service/app.py:63-65`、`fault-injection/inject_fault.py:15-23`。
- **Problem**: 无一真实制造资源耗尽/真实慢查询；故障名写进日志行形成泄漏（"pool exhausted (fault injected)" 被日志工具读回）。
- **Why It Matters**: "故障是真的吗"是本审计核心问题；假故障让"诊断能力"无从谈起（诊断=读日志字符串）。
- **Recommended Change**: 分两期——第一期（旗舰两个）：redis 用 `ConnectionPool(max_connections=2)`+并发占满真实打满；cpu 用 busy-loop 线程（真实 CPU）；同时把故障日志改为不含结论的中性表述（或由 agent 从 metric 侧获取证据）。第二期：slow_sql 接真 DB（demo 库）执行真慢查询或删除该 case 类型；memory 改常驻增长到阈值以上。
- **Tests Required**: 故障启用后对应 metric 真实越阈的断言（Prom 查询）。
- **How To Verify**: 注入后 `curl prometheus /api/v1/query` 看到对应指标越限。
- **Estimated Effort**: L（可分期，第一期 M）
- **Dependencies**: FI-03（规则对齐）。

### P0-09
- **ID**: P0-09（源 T-03 + AR-05）
- **Severity**: P0
- **Category**: Reliability / Agent
- **Current State**: checkpoint 仅在 run 结束后保存；load 生产零调用；verify 从空 state 起跑；文件写非原子；"crash recovery 测试"是 JSON roundtrip。
- **Evidence**: `runner.py:35-44`、`main.py:137-142`、`checkpoint.py:53-62`、`test_crash_recovery.py:16-41`、grep load 零调用。
- **Problem**: Agent crash 后无法恢复；声称能力不存在。
- **Recommended Change**: 方案 A（实现）：save 改 tmp+rename 原子写 + run 中每步 save + diagnose 入口先 load 续跑 + kill-restart 测试。方案 B（诚实降级）：删除"crash recovery"表述，文档改为"run 结束后持久化状态"。价值取 A。
- **Estimated Effort**: S-M（A）/ S（B）
- **Dependencies**: MQ-02。

### P0-10
- **ID**: P0-10（源 TS-01，tool-server）
- **Severity**: P0
- **Category**: Tool / 证据真实性
- **Current State**: `/api/k8s` 返回 dryRun 假数据（从不调 K8s API）；`/api/db` 返回硬编码 42/假慢查询；`/mcp` 多数工具 dryRun；审批校验仅 len>=8。
- **Evidence**: `tool-server/app.py:76-97,38-56,16,80-84`。
- **Problem**: agent 的 k8s/db 证据是编造的；MCP/审批是装饰。
- **Why It Matters**: 证据层虚假直接否定 Evidence-Driven 主张；也"意外地"掩盖了 P0-04/05 的安全风险（dryRun 无副作用）。
- **Recommended Change**: k8s 用 in-cluster ServiceAccount（复用 `tool-server-rbac.yaml` 的最小权限 Role）实现 list_pods/get_deployment/get_events 真实读取，写操作维持审批+dryRun 开关但如实标注；db 用真 DB 连接执行只读查询（active_connections/slow queries 来自 pg_stat_activity/pg_stat_statements）；compose 注入三个 `*_TOOL_URL`（顺带修 DOC-04）。
- **Estimated Effort**: M
- **Dependencies**: K8S 系列（若在 K8s 验证）；compose 环境可先用 docker socket 替代或保留 dryRun+标注。

### P0-11
- **ID**: P0-11（源 DOC-01）
- **Severity**: P0
- **Category**: Documentation 真实性
- **Current State**: 4 份文档宣称 Testcontainers "BUILD SUCCESS/通过"；留存 9 份日志全部 BUILD FAILURE（redis:7-alpine 容器启动失败）。
- **Evidence**: `docs/docker-validation.md:96`、`docs/coverage.md:23`、`docs/implemented-features.md:407`、`docs/baseline-before-hardening.md:26` vs `.mvn_it_dind6.log`。
- **Recommended Change**: 改回 ❌ 并注明失败原因；修复后重跑归档（T-04 一并处理）。
- **Estimated Effort**: S

### P0-12
- **ID**: P0-12（源 GIT-01，主审计发现）
- **Severity**: P0
- **Category**: Engineering Hygiene
- **Current State**: 仓库 0 commit（master unborn），全部文件 untracked；AGENTS.md 要求的 Git 工作流无从执行；CI 从未触发；任何修改无法回溯。
- **Evidence**: `git rev-parse --git-dir` 失败 / `git log --all` 为空；`.gitignore` 存在但未生效于任何历史。
- **Recommended Change**: `git init` + 首次提交（先扩充 .gitignore：`.docker_*.log` `.k6_*.log` `.mvn_*` `.dind*` `.tmp/` `.conda-cache/` 等 60+ 调试产物；确认 `.env` 不入库）→ 此后所有 Roadmap 工作按 AGENTS.md 分支+小步提交。
- **Estimated Effort**: S（0.5h）
- **Dependencies**: 无（是其余一切工作的前提）。

---

# P1 Issues（完整但紧凑）

| ID | 类别 | 问题 | 关键证据 | 修复方向 | Effort |
|---|---|---|---|---|---|
| CP-06 | 并发 | Approval.decide check-then-act 竞态→双重执行 | `ApprovalService.java:53-84`；无 @Version | 条件 UPDATE WHERE status='PENDING' 或 @Version；并发单测 | S |
| CP-07 | MQ | MQ 发送在 ingest 事务内，双写不原子；send 失败=告警丢失 | `AlertService.java:44,74`、`RocketMqAgentJobProducer.java:55-72` | afterCommit 发送或 outbox（AgentTask 表即 outbox 候选）；producer 启动失败不应阻断应用（NEEDS VERIFICATION: @PostConstruct 行为） | M |
| CP-08 | MQ | 幂等键含 UUID 失效；任务无 RUNNING/FAILED；VERIFICATION 类型不走 MQ | `RocketMqAgentJobProducer.java:47`；`AgentTaskController.java:29-36` | 键=diag-incidentId；消费侧回写状态 | S |
| CP-09 | 正确性 | LIKE 错绑 incident + 并发重复创建 | `IncidentRepository`、`AlertService.java:87-93,71-73` | 精确匹配+startedAt 条件；条件 insert/唯一约束 | S-M |
| CP-10 | 并发 | 无 @Version；setStatus 绕过状态机；非法流转静默忽略 | grep @Version=0；`AgentResultService.java:67-69,228-232` | @Version+条件 UPDATE；非法流转 409 | S |
| CP-11 | 事务 | 事务内 HTTP 副作用（auto-remediation/verify），回滚后无痕 | `AgentResultService.java:64,144,153`（NPE 路径）、`RemediationExecutor.java:62,86-101` | 提交后事件驱动或 REQUIRES_NEW 先落行；rootCause null 校验（CP-18） | M |
| CP-12 | 审批 | 无过期；REJECT 悬挂 WAITING_APPROVAL；decidedBy 可伪造；重复 PENDING 堆积 | `ApprovalService.java:53-84`、`AgentResultService.java:120-131` | expiresAt+校验；REJECT 回退+审计；decidedBy=JWT sub；PENDING 复用 | S-M |
| CP-14 | 安全 | AuthZ 矩阵过宽：全部 GET/actuator/tasks complete/alerts 无 secret | `AuthInterceptor.java:23-35`、`application.yml:32-36` | 读端点≥VIEWER；complete 需 agent token；alerts 共享 secret；actuator 独立端口 | M |
| CP-15 | Redis | dedup fail-closed（Redis 挂=告警 500）且不 gate 写入 | `RedisDeduplicationStore.java:21`、`AlertService.java:47,80,82` | try/catch 降级 fail-open+WARN+指标；firstSeen 真正抑制重复 | S |
| CP-16 | 可观测 | CP 全模块零日志；7 处吞异常 | grep LoggerFactory=0；`RemediationExecutor.java:77-82,99-101` 等 | SLF4J 全量接入；catch 处 warn/error 带堆栈 | S |
| CP-17 | DB | ddl-auto=update 与 Flyway 双轨且实体漂移 | `application.yml:10,12-15`；`Alert.java:43-44` vs `V1:29` | 生产 validate；实体对齐；CI validate 启动断言 | S |
| CP-18 | 校验 | 无 spring-boot-starter-validation；DTO 无约束；Map.of null NPE | pom；`AgentResultService.java:153` | 引 validation+@NotBlank；null 安全 | S |
| AR-04 | LLM | 无重试接线；Timeout 空壳 | `main.py:50-58`、`llm/base.py:29-39` | 包 RetryLLMProvider+真实 timeout+429 退避 | S |
| AR-05 | 消费 | submit 失败仍 complete（丢结果）；mark 顺序错；文件非原子 | `consumer.py:51-54,78-81`、`idempotency.py:41-45` | 失败不 complete+重试；tmp+rename | S-M |
| AR-06 | 验证 | 验证非确定性（无 SLI/无观察窗/空 state） | `verification.py:19-56`、`main.py:137-142` | 确定性 SLI+window+LLM 解释（见 Reliability 建议） | M |
| AR-07 | 工具 | timeout 不强制；限速进程内 | `tools/base.py:16,27-47` | executor 强制超时 | S |
| AR-08 | 安全 | prompt 注入面（无指令/数据隔离） | `context.py:29-45` | system 声明+包裹标记+可疑语句标注 | S |
| MQ-01 | MQ | 消费端从未启用（依赖缺失），链路是轮询 | `requirements.txt`、`mq_consumer.py:15-19`、`.rocketmq_test.log` | 见 Reliability MQ-01 | S/L |
| MQ-02 | 分布式 | 任务无 claim → 多副本重复执行 | `AgentTaskController.java:24-27`、HPA max 5 | claim/lease+条件更新+超时回收 | M |
| MQ-03 | MQ | 毒消息无限 RECONSUME、无 DLQ 处理、幂等存储非原子 | `mq_consumer.py:28-41` | 最大重试+DLQ 告警+DB 幂等 | M |
| FI-03 | 告警 | 故障-规则错位（cpu sleep→HighCPU 永不触发；memory 30MB vs 500MB） | `prometheus-alerts.yml:39-59` vs `inventory-service/app.py:61-66` | 修机制（P0-08）或对齐阈值/指标（cAdvisor） | S |
| FI-04 | 日志 | Loki 零写入者，query_logs 恒空 | `otel-collector.yml:25-34`、grep promtail=0 | loki docker driver 或 promtail；或 collector filelog+loki exporter | S-M |
| FI-05 | 指标 | remote-write receiver 未开（404）；无 OTel metrics | compose prometheus 命令、`otel-collector.yml:20-34` | 加 flag；demo 加 MeterProvider（可分期） | S |
| FI-06 | 告警 | 3 条幻影 metric 规则（无 exporter） | `prometheus-alerts.yml:61-92` | 加 redis/postgres/rocketmq exporter 或删规则 | S |
| T-01 | 测试 | 210/252 Python 用例为生成重复模板；计数文档漂移 | `generate_extended_tests.py`、docs 222/233/240 | 删生成物；文档以最近一次 CI 输出为准 | S |
| T-02 | 测试 | Java 核心链路 0 测试（Alert/AgentResult/Approval/Remediation/Auth） | `src/test` 仅 3 类 | @SpringBootTest+Testcontainers 补主链 | M-L |
| CI-01 | CI | lint 装而不跑；无 web build job | `ci.yml:24-29` | `ruff check`+`npm run build` job | S |
| FE-01 | 前端 | React 死代码+web 镜像产物损坏 | `vite.config.js`、实测 build、`docker-compose.yml:90-98` | 双轨二选一定版；Dockerfile npm ci | S |
| DOC-04 | 文档 | 架构图工具链路失实+三工具 URL 未注入 | `builtin_tools.py`、compose env | 修图+注入 `*_TOOL_URL`（随 P0-10） | S |
| DOC-05 | 文档 | MQ 主链路失实 | `main.py:61-66` | 标注轮询为事实链路（随 MQ-01） | S |
| DOC-06 | 文档 | security.md 过强声称（一次性 token/审批校验/脱敏） | `ApprovalService.java:68`、`tool-server/app.py:80-84` | 随 P0-04 修复后重写 | S-M |
| DOC-07 | 文档 | production-readiness-audit.md 全面过时 | 全文 | 按本审计重写 | M |

---

# P2 Issues（紧凑表）

| ID | 问题 | 证据 | 方向 | Effort |
|---|---|---|---|---|
| CP-19 | SSE 无心跳/无 onError/串行阻塞/无重放 | `IncidentEventService.java:13-33` | 心跳+onError（多实例时 Redis pub/sub） | S |
| CP-20 | 三处 findAll 全表扫描 | `IncidentService.java:31-33` 等 | 派生查询 countBy* | S |
| CP-21 | 健康检查双实现+串行 12s+恒 ok | `DashboardService.java:25-71`、`HealthController.java` | 统一配置+并行+依赖检查 | S |
| CP-22 | 死代码群（Runbook/EvaluationCase 实体+repo、updateRootCause、Incident.report、包装类） | grep 零引用 | 删或接线并声明 | S |
| CP-23 | Agent 链路断链（taskId=0L、riskLevel 恒 READ_ONLY） | `AgentResultService.java:97,109` | DiagnosisRequest 带 taskId；riskLevel 由 policy 填 | S |
| CP-24 | 测试风险倒挂（审批/修复/鉴权 0 测试） | `src/test` | 见 T-02 | L |
| CP-25 | 魔法字符串状态/rocketmq.* 死配置/裸 mvn 缺驱动 | `application.yml:24-27`、pom profiles | 枚举+配置清理 | S |
| AR-09 | Evidence 无 timestamp/query/time_range；status 恒 ROOT_CAUSE_FOUND | `models.py:23-27`、`diagnostic.py:161-171` | 字段扩展+status 语义 | S |
| AR-10 | Planner 语义装饰 | `planner.py` | 并入诊断或真规划（LLM function calling 时自然消解） | S |
| AR-11 | mcp_client 主链路零调用 | grep | 删或接线 | S |
| FI-07 | chaos YAML 零执行 | grep chaos | 删或标注 experimental（K8s 实跑后再启用） | S |
| FI-08 | monitoring the monitor 缺位（无 metrics/scrape/dashboard/自监控告警） | `prometheus.yml:15-28` | AR/TS /metrics+scrape+up 告警+1 dashboard | M |
| FI-09 | SLO 无 recording rule | `prometheus-alerts.yml` | sli:* recording rules+budget | M |
| FI-10 | 评估期望证据与真实机制脱节（redis_slowlog 恒空） | `cases/redis_slow_001.yaml` vs `payment/app.py:73-75` | 随 P0-08 对齐 | M |
| T-04 | 集成测试只验容器启动且 CI 不跑 | `ControlPlaneIntegrationTest.java:23-30` | 迁移+仓库冒烟；CI 加 integration | S-M |
| T-05 | contract test 校验 mock 自身 | `test_local_contract.py:25-46` | 对真 CP 跑（Testcontainers） | M |
| FE-02 | Playwright 不可运行且断言错位 | `web/e2e/dashboard.spec.js`、lock | 定版后重写冒烟 | S |
| FE-03 | SSE 主动断连；React 无错误态；无 401 处理 | `app.js:384`、`App.jsx:38-46` | 修 onerror；统一错误包装 | S |
| E2E-01 | 假 E2E 被当"真实闭环"宣传并进 CI | `local_e2e_runner.py:223-238` | 更名"契约冒烟"；真闭环只认 RUN_E2E | S |
| BM-02 | benchmark 压 mock、无阈值、无 raw 落盘 | `agent-benchmark.py:36-41` | --output/阈值/分层标注 | S |
| BM-03 | qps 公式错；SSE 压测无意义；alert 阈值击穿未披露 | `local_api_load_runner.py:44-49`、`.k6_alert3.log` | 修公式；如实记录 | S |
| CI-02 | CI 无任何真实集成（compose/E2E/k6/eval 全靠手动） | `ci.yml` | nightly integration job | M |
| CI-03 | CI 从未触发（0 commit） | git log | 随 P0-12 | S |
| DOC-08 | 测试数漂移；结果文件不入仓；k6 失败未披露 | docs 三处 | 统一口径+结果入仓 | S |
| DOC-09 | 故障表/Tool 说明与代码偏差 | `implemented-features.md` | 更新 | S |
| DOC-10 | README Future Work/limitations/runbooks 陈旧矛盾 | 三文档 | 清理 | S |
| GIT-02 | 根目录 60+ dot-log 调试产物未 ignore | `ls -a` | 扩 .gitignore+归档清理 | S |
| K8S-01 | default-deny 疑断 DNS；缺 tool-server/frontend Deployment 与数据层；latest；无 liveness/securityContext | `deploy/k8s/*.yaml` | 修 DNS egress；补缺；pin+probe；kind/minikube 实测部署 | M-L |

---

# P3 Issues（一行式）

- CP-25a：状态魔法字符串 → 枚举。
- FI-11：无 redis span / access log 无 traceId / X-Request-Id 恒 "-"（`requirements.txt:4-9`、`gateway/app.py:29`）。
- FI-12：AM 分组粒度弱（resource 静态 demo-service；HighCPU/HighMemory 无 service 标签）。
- T-06：真实 E2E 断言弱（不校验 root cause 内容）+ 时长 flaky（`test_real_faults.py:166,217,256`）。
- T-07：并入 P0-03。
- CI-04：无缓存；python 3.11 vs 本地 3.13；run_all_local_tests 重复跑单测。
- CI-05：scan-secrets.ps1/kubeconform 未接 CI。
- FE-04：API base 无注入点；timeline 时间戳失真（`app.js:268-299`）。
- DOC-11：.env 真实 API key（未入库）→ 轮换 + scan 接 CI。
- DOC-12：api-contract 漏 2 端点；api.md 调用方向画反。
- AR-12：mock LLM 答案与 case 期望同源（随 P0-03 一并处理文档披露）。
- EV-02：incident_id 用 PYTHONHASHSEED 敏感的 `hash()`（`run_evaluation.py:48`）。
- 备份/恢复：脚本存在但无恢复演练自动化（`scripts/backup-db.ps1`）。

---

# Top 20 改进项（按收益排序）

| Rank | Task | Priority | Why | Effort | Impact | Dependencies |
|---|---|---|---|---|---|---|
| 1 | P0-12 git init+首次提交+ignore 调试产物 | P0 | 一切工程化前提；CI/回滚/审查的基座 | S | 全局 | — |
| 2 | P0-03 Evaluation 重构（canonical 标签+去泄漏+真 top3+splits+产物落盘） | P0 | 没有 AI 可信度就没有项目可信度；评审第一深挖点 | M | 极高 | 3,4 |
| 3 | P0-01 规则兜底降级（去 0.8/去伪证据） | P0 | 让"Agent 推理"与"规则兜底"诚实可分 | S | 极高 | — |
| 4 | P0-02 工具参数 alert 驱动 | P0 | 证据链源头修复，~30 行 diff 改变诊断正确性 | S | 极高 | — |
| 5 | P0-05 Agent 回调 token+幂等 | P0 | 堵住重放/多副本重复执行修复的确定性风险 | M | 高 | 10 |
| 6 | P0-04 审批参数绑定+fail-closed+token 强化 | P0 | 审批闸门从装饰变真实；安全故事成立 | M | 高 | 5 |
| 7 | P0-06 JWT exp+启动校验+BCrypt | P0 | 三行级 bug 级安全修复 | S-M | 高 | — |
| 8 | P0-07 AM 适配端点+全链路 E2E | P0 | 打通"从真实告警开始"的叙事起点 | M | 高 | — |
| 9 | CP-16+CP-18 全链路日志+输入校验 | P1 | 生产可运维底线；排障前提 | S | 高 | — |
| 10 | MQ-02 任务 claim+MQ-01 消费端决策落地 | P1 | 分布式系统叙事从"画的"变"跑的" | M-L | 高 | 5 |
| 11 | CP-07 afterCommit/outbox | P1 | 双写原子性；评审必查 | M | 高 | 10 |
| 12 | P0-10 tool-server 真数据（k8s SA+真实 db 只读） | P0 | 证据层从假变真；MCP/审批故事复活 | M | 高 | 6 |
| 13 | T-02 Java 核心链路测试（@SpringBootTest+Testcontainers） | P1 | 最高危链路从 0 覆盖到可回归 | M-L | 高 | 9 |
| 14 | FI-04 日志进 Loki | P1 | 日志证据从恒空变可用；traceId 关联落地 | S-M | 高 | — |
| 15 | FI-02 一期 REAL 故障（redis pool+cpu busy-loop） | P0(分期 P1) | "故障是真的"——诊断对象真实化 | M | 高 | 14, FI-03 |
| 16 | AR-06 确定性验证+观察窗 | P1 | "恢复"从 LLM 猜测变 SLI 事实 | M | 中高 | 4,15 |
| 17 | FI-08 self-monitoring+1 张 Grafana dashboard | P1 | monitoring the monitor 从 0 到 1 | M | 中高 | — |
| 18 | CI-01/02/05 lint+web build+nightly 集成+secret 扫描 | P1 | CI 从"从未触发"到可信门禁 | S-M | 中高 | 1 |
| 19 | FE-01 前端定版（vanilla 或 React 二选一）+FE-03 重连/401 | P1 | 控制台可信+代码量减半 | S | 中 | — |
| 20 | DOC 全系诚实化（DOC-01~10）+T-01 删生成测试 | P1 | 文档不再领先现实；测试计数可信 | S-M | 中 | 各项落地后 |

**如果只有 2 周**：做 Rank 1-9 + 14 + 19（约 8-10 个工作日）——项目性质从"演示"变"可信"；P0-08 故障真实化做到一期（redis+cpu），P0-10 做到 k8s 真读（compose 环境可先用文档标注）。
**如果有 1 个月**：完成全部 Top 20 + K8S-01（kind 部署实测）+ P0-08 二期 + 备份恢复演练 + 压测口径修正，然后**停止加功能**（见 Do Not Build Yet），转入评审材料与 Demo 脚本打磨。

---

# Roadmap（2-4 周分阶段）

## Stage 1 — Critical Correctness（第 1 周前半，~4 天）
P0-12 → P0-01/02/03（评估真实化）→ P0-06 → CP-16/18 → 文档虚假项即刻更正（DOC-01/02/03）。
验证：`run_evaluation` 在 test split 产出可信数字；过期 token 被拒；LLM 挂掉时输出 unknown 而非 redis。

## Stage 2 — Reliability（第 1 周后半，~4 天）
P0-05 + MQ-02（claim）→ CP-06/07/08/09/10/11 → CP-15 → AR-05 → P0-09（选实现路线）。
验证：kill agent-runtime 中途 → 恢复后不重复执行；双副本领取无重复；Redis 挂掉告警仍接入。

## Stage 3 — Security & Approval（第 2 周前半，~3 天）
P0-04 + P0-10（tool-server 真数据）→ CP-12/13/14 → AR-08。
验证：幻觉动作不执行；审批参数=执行参数；匿名回调 401。

## Stage 4 — Observability & Formal Chain（第 2 周后半，~3 天）
P0-07 → FI-04 → FI-03/05/06 → FI-08 → FI-09（最小 recording rules）。
验证：Prom 规则触发→AM→CP→Agent 全链路一条 E2E 绿；Grafana 有 1 张 dashboard；agent-runtime 被监控。

## Stage 5 — Fault Truth & Testing（第 3 周，~5 天）
P0-08 一期（redis pool 真打满 + cpu busy-loop）→ FI-10 对齐评估期望证据 → T-02 Java 主链测试 → CI-02 nightly 集成 → T-01 清理生成测试。
验证：注入后 Prom 指标越限；Agent 在**不带答案标签**的输入上靠证据得出根因。

## Stage 6 — Deploy & Portfolio Polish（第 4 周，~5 天）
K8S-01（kind 实测部署+修 default-deny/补缺）→ CP-17/20/21/22 → FE-01/02/03 → BM 口径修正+结果入仓 → DOC-07 重写 + README/架构图重绘（含 Mermaid Target Architecture）→ 技术深挖材料（每个 Findings 一段"为什么这样修"）。
验证：全新机器 compose up + kind deploy 双路径可复现；文档与代码零矛盾。

---

# Do Not Build Yet（现在不要做）

1. **Service Mesh / Istio**——单 compose 栈，NetworkPolicy+OTel 已够。
2. **复杂 Workflow 引擎（Temporal/Camunda）**——当前状态机+任务表足够；先把 claim/幂等做对。
3. **更多 Agent（修复 Agent/复盘 Agent/多 Agent 协作框架）**——先把现有三个变真；Multi-Agent 已是 PARTIAL，再加只会稀释。
4. **更多向量库/重写向量层（Milvus/Qdrant）**——pgvector 都还没接线；先接 pgvector + 真 embedding。
5. **复杂 Memory 系统**——当前会话级 context 足够；先修 context 的指令/数据隔离。
6. **前端重写第二遍**——双轨定版后冻结；CSS/组件库打磨不是瓶颈。
7. **Chaos Mesh 扩展/更多 chaos 实验**——K8s 部署未实测前全是纸面；先 pod-kill 一个实验在 kind 跑通即可。
8. **更多评估 case（>200）**——评分失真时更多 case 只会放大失真；先修 P0-03。
9. **MCP 扩展（resources/prompts/sampling/多 server）**——当前 MCP 是 COSMETIC；先让 tools/call 真实。
10. **云原生平台（K8s Operator/多集群/Helm chart 体系）**——kind 单集群跑通前不做。
11. **多副本 HPA 扩容演练**——在 MQ-02 claim 落地前，扩容=重复执行放大器；先修再扩。
12. **生产级 RBAC/多租户/SSO**——三角色够用，先让现有矩阵生效（CP-14）。

---

# Target Architecture（只做必要调整）

**Current Architecture**（即上方 Project Map，断点：MQ 无消费者、AM 契约断裂、Loki 无写入者、tool-server 假数据、无任务 claim）。

**Recommended Target Architecture**（改动以 ★ 标注，其余保持现状）：

```mermaid
flowchart LR
    subgraph 观测面
        PROM[Prometheus ★+recording rules+remote-write receiver+3 exporter 或删幻影规则]
        AM[Alertmanager]
        LOKI[Loki ★+loki-docker-driver/promtail]
        JAE[Jaeger]
        GRAF[Grafana ★≥1 dashboard + self-monitor]
    end
    AM -->|"★ POST /api/v1/alerts/alertmanager 契约适配"| CP
    PROM -->|scrape| DEMO
    PROM -.->|"★ scrape + /metrics"| CP2[Control Plane]
    PROM -.->|"★ scrape"| AR2
    subgraph 编排面[Control Plane Java]
        CP[AlertController ★AM-DTO<br/>AlertService ★精确匹配+条件insert<br/>★dedup fail-open]
        CPDB[(PG ★ddl validate)]
        OUTBOX[AgentTask ★=outbox<br/>★afterCommit 发送]
        CP2[AgentResultService<br/>★回调token+幂等键<br/>★状态机强制+@Version]
        AP[Approval ★payload绑定+过期<br/>★fail-closed RiskPolicy]
        REM[RemediationExecutor<br/>★POST+参数化+header token<br/>★事务外执行]
    end
    CP -->|★MQ 真实消费 或 显式轮询| MQ[[RocketMQ ★消费者启用+DLQ]]
    MQ --> AR
    OUTBOX --> MQ
    subgraph 推理面[Agent Runtime Python]
        AR[Consumer ★claim/lease+RUNNING/FAILED]
        AR2[DiagnosticAgent ★LLM function calling 参数<br/>★兜底降级 fallbackUsed]
        VER[Verification ★确定性SLI+观察窗+LLM解释]
        CHK[Checkpoint ★原子写+resume]
        RAG[Retriever ★真embedding(pgvector) 可选<br/>★chunking+metadata]
    end
    subgraph 工具面[Tool Server]
        TS[★k8s: 真K8s API(SA+RBAC只读)<br/>★db: 真DB只读查询<br/>★redis: 已真实<br/>★写操作: 审批token绑定+审计]
    end
    AR -->|直连 P/L/J ★+tool-server| TS
    TS --> K8S[(K8s API ★只读)]
    TS --> REDIS[(Redis)]
    TS --> PG[(Demo DB ★真实慢查询)]
    AR -->|★回调带token+taskId| CP2
    DEMO[gateway/order/inventory/payment<br/>★REAL故障: redis pool打满+cpu busy-loop]
    REM -->|★审批通过后| TS
    VER -->|★SLI证据| PROM
```

不改变：四层组件边界、审批流、静态 RiskPolicy 立场、SSE（单实例）、vanilla 前端、200 case 数据集底座、告警史落库设计。

---

# 三个核心问题的回答

## Q1：距离"高质量生产级项目"还缺什么？

1. **可信的 AI 能力证据**：非泄漏评测数字（P0-03）、真故障上的诊断正确性（P0-08）、真实 LLM 全链路证据（真 embedding/RAG 贡献量化）。
2. **可靠后端语义**：幂等回调、任务 claim、双写原子性、崩溃恢复（P0-05/09、MQ-02、CP-07）——这些是技术评审"重复消费怎么办/挂了怎么办"的直接答案，现在是空的。
3. **真实生效的安全边界**：审批参数绑定、fail-closed、token 校验（P0-04/06）。
4. **文档与代码零矛盾**：现在有三处会被当场戳穿的虚报（DOC-01/02/03）。
5. **版本管理与 CI 运行记录**（P0-12、CI-03）——"0 commit"在技术评审中是硬伤。

## Q2：距离"可以真正部署运行"还缺什么？

按依赖序：① git 基线；② AM 适配（正式链路 500）；③ 任务消费可靠性（claim+幂等）否则多副本=重复修复；④ tool-server 真数据（否则"修复"与"证据"是假的）；⑤ K8s manifest 修复（DNS egress、补缺失负载）+ kind 实测部署；⑥ secret 注入（jwt/口令/LLM key）与备份恢复演练；⑦ self-monitoring（否则部署后平台自身是盲的）。compose 单机路径已经基本可跑（P0-07 修复后即可完整演示）。

## Q3：哪些改动投入产出比最高？

**一周内**：P0-12（0.5h）+ P0-01/02（各 0.5d）+ P0-03（2-3d）+ P0-06（0.5d）+ CP-16/18（1d）。这 5 项 ≈ 5 个工作日，直接把「评测可信、RCA 诚实、证据对准、认证有效、可排障」五个最致命的短板补掉。
**其次**：P0-04/05（审批安全闭环，2-3d）与 P0-07（正式链路打通，1d）——它们决定项目叙事的"闭环"是真是假。
**不建议现在投入**：Do Not Build Yet 清单中的全部 12 项。

---

*本审计由主审计 + 4 子审计完成，全程只读；所有 `NEEDS VERIFICATION` 项已在正文标注。配套任务清单见 `docs/improvement-roadmap.md`。*
