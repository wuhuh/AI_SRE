# Improvement Roadmap（可独立完成与验证的任务清单）

来源：`docs/project-audit.md`（2025-09 全面技术审计）。
使用方式：每项可单独完成并验证；完成一项勾一项。阶段划分见 audit 的 Roadmap 章节。
验证列给出了每项的最小验证命令/观察点；涉及改代码的项，按 AGENTS.md 走分支 + 小步提交（本清单建立前先做 GIT-01）。

# P0

- [x] **P0-12 (GIT-01) git 基线**：`git init` + 扩充 `.gitignore`（调试产物/临时状态/env/node_modules）+ 首次提交。
  ✅ 已完成（commit 33392f3，468 文件入库；文档引用的证据归档至 `docs/evidence/` 并附 README 溯源）。注意：git 身份暂用 `pzz <pzz@localhost>`，推送前请修改 `git config`。

- [x] **P0-01 (AR-01) 规则兜底降级与去伪证据**：`_finalize` 删除 confidence→0.8 改写与伪造 rule 证据；LLM 失效/未知/超时 → `unknown` + `confidence≤0.3` + `fallbackUsed=true` + `heuristicCandidate`，且不给修复建议。
  ✅ 已完成（commit 284889e；DiagnosisResult 新增 fallback_used/heuristic_candidate；test_fallback.py 4 用例 + test_llm_instability 更新；257 tests OK）。

- [x] **P0-02 (AR-02) 工具参数由 alert 驱动**：Diagnostic/Verification 工具参数取自 `alert.service`；PromQL 对齐 demo 实际指标（旧模板引用的 `http_server_requests_seconds_count` 在 demo 中不存在，恒查空）；latency 类告警自动选 p95 histogram。
  ✅ 已完成（commit eea6a07；tests/test_tool_arguments.py 4 用例；run_baseline monkeypatch 同步修复）。

- [x] **P0-03 (AR-03/BM-01/DOC-02/DOC-03/T-07) Evaluation 重构**：
  ✅ 已完成（commits 97af788 / 8b9effa / 3b1a2b3）：
  ① Agent 侧 canonical 标签约束 + alternatives（真实 Top-3 依据）+ 真实 token 计量；
  ② 输入无泄漏（中性 symptom 档案，fault_type 绝不进 alert）+ 精确标签打分（删双向子串）+
  splits 支持 + 结果落盘 evaluation/results/ + Unknown/Evidence P·R/tool 成功率/P95 指标；
  ③ 顺带修复：`_finalize` 对真实 LLM 形状漂移 500（evidence 字符串列表等）、
  `--agent-url` 未接线、诊断预算 env 旋钮（DIAG_BUDGET_SECONDS）；
  ④ **实测（test split, 20 例）**：openai/deepseek-v4-flash **Top-1=0.70、Top-3=0.70、Unknown=0.30、
  Evidence Recall=0.00**；mock 基线 Top-1=0.05。结果见 docs/benchmark.md 新节。
  遗留（转入后续项）：6 个 unknown 集中于 cache/db 类故障（LLM 循环超步）；Evidence key 与期望零交集；
  Top-3 从未救回 miss（alternatives 质量 OK 但 miss 均为 unknown 而非自信错答）。
  验证：`python evaluation/runner/run_evaluation.py --splits test` 输出报告 + 结果 JSON 入仓；
  `python3 -m unittest discover -s evaluation/tests`（11 离线用例，含泄漏防护）。
  Effort: M（2-3 天）

- [x] **P0-04 (CP-01+CP-02+CP-13) 审批参数绑定 + fail-closed + token 强化**：
  ✅ 已完成（commit a3cd2c8）：payload 由 incident.service 驱动（namespace/deployment/pod/replicas）；
  执行改 POST+JSON body+X-Execution-Token header（token 不再进 URL）；删 default 兜底 ——
  未知动作不发请求，FAILED + UNKNOWN_ACTION_REFUSED 审计；RiskPolicy 未知→HIGH_RISK；
  redis/db 占位假执行（command=info）一并 refuse；tool-server 删 len≥8 放行、写操作仅 POST+精确匹配。
  测试：RiskPolicyTest(2) + RemediationExecutorBodyTest(4) + tool-server 6 用例（Java 27 OK）。
  遗留：真实 K8s 执行（dryRun→真调用）在 P0-10/P0-11 范围。
  Effort: M

- [x] **P0-05 (CP-05) Agent 回调鉴权 + saveDiagnosis 幂等**：
  ✅ 已完成（commit 3c21bb8）：X-Agent-Token 常量时间比较（未配置 token 时 fail-closed 503）；
  DiagnosisRequest+taskId 且 AgentStep 记录真实 taskId；saveDiagnosis 幂等 —— 状态已到
  ROOT_CAUSE_FOUND 及之后的重复回调直接返回现状，不再追加重复 evidence/审计；
  /tasks/* 全部纳入 agent 回调面。测试：AuthInterceptorTest(5)。Java 21 OK / Python 265 OK。
  Effort: M

- [x] **P0-06 (CP-03+CP-04) 认证修复**：JWT exp 用 Jackson 解析（数字）；启动时 strict 模式校验 `aisre.jwt.secret` 非默认且 ≥32B、口令非默认（否则 fail-fast）；口令支持 BCrypt（$2 开头）+ 明文兼容；登录失败限速（10min 内 5 次锁定）。
  ✅ 已完成（commit 2421e18；compose/K8s strict=true + secret 注入；附带修复 control-plane.yaml 原有 YAML 缩进错误——该 manifest 此前无法通过解析。Java 16/16 tests OK）。
  Effort: S-M

- [x] **P0-07 (FI-01) Alertmanager 契约适配 + 全链路 E2E**：
  ✅ 一期完成（commit ac45a53）：`POST /api/v1/alerts/alertmanager`（AM v4 契约）+
  AlertmanagerAdapter 映射（labels.service→service_name→job→unknown、resolved 跳过、
  复用 5min 去重/聚合）+ 契约测试 5 用例（Java 36 OK）。
  ⚠️ 遗留：「注入故障→Prom 规则→AM→CP→Agent」全链路 E2E 需要 docker 环境
  （本机 WSL 无 docker），到有 docker 的环境补跑并归档日志。

- [x] **P0-07 (FI-01) Alertmanager 契约适配 + 全链路 E2E**：
  ✅ 一期完成（commit ac45a53）：`POST /api/v1/alerts/alertmanager`（AM v4 契约）+
  AlertmanagerAdapter 映射（labels.service→service_name→job→unknown、resolved 跳过、
  复用 5min 去重/聚合）+ 契约测试 5 用例（Java 36 OK）。
  ✅ 全链路 E2E 完成（docker 环境闭环）：停止 payment-service（真实故障）→
  Prom ServiceDown 规则 → AM webhook（alertmanager.yml 已指向适配端点）→ CP 建档建任务 →
  agent claim+诊断（真实工具链）→ 风险分级 → restart_pod 经 tool-server **真实重启容器**
  （docker.sock 模式，executed=true）→ VERIFICATION_SAVED。修复项：prometheus.yml
  每目标补 service 标签、LokiTool 相对时间 400、TraceTool Tempo 端点 404、
  Java HttpClient h2c 升级丢 body（锁 HTTP/1.1）、审批 operator 空值炸审计、
  共享执行 token。

- [x] **P0-08 (FI-02 一期) REAL 故障：redis pool + cpu**：
  1. payment-service 用 `redis.ConnectionPool(max_connections=2)` + 故障启用时并发占满（真实打满）；
  2. inventory-service cpu_saturation 改为 busy-loop 线程（真实 CPU 上升）；
  3. 故障日志改为中性表述（不含结论词），根因证据改由 metric 侧获取。
  ✅ 一期完成：
  - inventory `cpu_saturation` 改为 uvicorn 进程内 sha256 busy-loop（`CPU_BURN_SECONDS`
    可调）——持续灌压下 `avg(rate(process_cpu_seconds_total))=0.83` 真实可见，
    禁用后回落 0.0014（验证含"禁用后恢复"）；payment 5xx 4.6/s 真实产生。
  - 真实故障 × 真实 LLM（openai/deepseek-v4-flash）诚实基线（14 case，中性告警）：
    **Top-1=57.1%，Top-3=64.3%，Unknown=21.4%**（cpu_saturation **7/7=100%**，
    redis 类 1/7 直接 + Top-3 共 2/7）。首轮 35.7% → 57.1% 的提升全部来自真实工程修复：
    LLM 读超时（15s→跟随预算）、Jaeger trace 400、agent 缺 redis 工具别名、
    编造工具名空转守卫。归档 `evaluation/results/eval_*_real-fault*.json`。
  - ✅ 二期（真打满，commit 0e2f39a 附近）：payment 改真实有界
    `ConnectionPool(max_connections=2)`，故障启用 = 后台 BLPOP 线程真实持占全部
    连接，/payments 收真实 "Too many connections"（redis 侧 blocked_clients=2
    真实证据，禁用回 0）。删除合成日志（伪造结论+标签泄漏）。
    redis 类 Top-1 **1/7 → 3/7（42.9%）**，Top-3 → 57.1%（real-fault-realpool）。
  - 遗留：Evidence Recall=0.00（证据 key 是工具调用序号而非语义 key，见 P2-FI-10）。
  Effort: M（二期 slow_sql/记忆泄漏：L）
  依赖：FI-03（规则对齐）、FI-04（日志可用性）

- [x] **P0-09 (T-03) Checkpoint resume（选实现路线）**：FileCheckpointStore 改 tmp+rename 原子写；`run_diagnosis` 每步 save；`/api/v1/agent/diagnose` 入口先 `load` 续跑（幂等标记）；补 kill -9 中途 → 重启 → 续跑集成测试。若决定降级：删除"crash recovery"表述并同步文档/测试改名。
  ✅ 已完成（commit 70ab78a，实现路线）：tmp+os.replace 原子写；AgentState+pending
  随 checkpoint 持久化；诊断循环每步落盘（on_step 回调，失败不中断诊断）；
  入口 load：已完成 → 幂等直接返回（不烧 LLM，duration 0 + resumed 标记）；
  中断 → 从剩余 pending 续跑，已完成工具不重放。测试 3 用例
  （模拟 kill -9 第二步 → 新 runner 续跑断言 tool_calls 不重复 / tmp 原子替换 /
  损坏 checkpoint 回退重跑）。Python 268 OK。

- [ ] **P0-10 (TS-01) Tool Server 真数据 + MCP 落地**：
  ✅ 部分完成（commit d09ca46）：db 真实只读查询（pg_stat_activity：health/
  active_connections/slow_query，原 42 等假数据删除，无 DSN 如实 503）；/mcp tools/call
  走真实后端；compose 注入 REDIS/DATABASE/KUBE_TOOL_URL；compose 模式 list_pods 经
  docker ps 返回真实容器清单（source=docker-compose，k8s in-cluster SA 待真 k8s 环境）。
  1. k8s：in-cluster ServiceAccount（复用 `tool-server-rbac.yaml` 最小权限）实现 get_deployment/get_events 真实读取；写操作保留审批 + dryRun 开关但如实标注；
  2. db：真实只读查询（pg_stat_activity / pg_stat_statements / EXPLAIN）；
  3. redis：保持（已真实）；
  4. `/mcp` tools/call 全部走真实后端；
  5. compose 注入 `REDIS_TOOL_URL/KUBE_TOOL_URL/DB_TOOL_URL` 指向 tool-server:8081。
  验证：compose 环境下 diagnose 的 evidence 中 k8s/db 条目包含真实数据（pod 名/连接数）；审批校验错误 token 403。
  Effort: M

- [x] **P0-11 (DOC-01) 撤销 Testcontainers 虚假记录**：
  ✅ 已完成（commit bacdda8）：docker-validation.md / coverage.md / implemented-features.md /
  baseline-before-hardening.md 四处改为 ❌ 未通过并引用 `evidence/mvn_it_dind6.log`
  （BUILD FAILURE，ContainerLaunchException: redis:7-alpine）。
  ✅ 闭环（commit 02cf492）：maven 容器挂宿主 docker.sock 真跑，
  testcontainers 1.21.3 + `-Dapi.version=1.44`（Docker 29 弃用 1.32 ping），
  **37/37 OK，BUILD SUCCESS**，新日志 `evidence/mvn_it_docker40.log`，
  四份文档已回填 ✅。
  Effort: S

# P1

- [x] **P1-CP-06** Approval.decide 并发竞态：✅ 条件 UPDATE `decideIfPending ... WHERE
  status='PENDING'`（0 行更新→409 "already decided"）。40/40 绿。
  验证：两线程并发 decide 仅一次执行的集成测试。
  Effort: S

- [x] **P1-CP-07** MQ 双写原子性：✅ outbox 模式——AgentTask 加 mq_status(PENDING→SENT)/
  mq_attempts（V5 迁移），发送移到事务 afterCommit；后台扫描器（10s）按上限补发
  （发送失败/提交后崩溃都覆盖）；producer 启动失败不再炸应用启动（懒重连解耦）。
  验证：注入 audit 失败断言消息未发出；MQ 宕机时告警接入仍 202（补发机制兜底）。
  Effort: M

- [x] **P1-CP-08** 任务幂等键与生命周期：✅ 幂等键 `diag-<incidentId>`（首键）+
  `-r<N>`（FAILED 重派，确定性序号）；唯一索引防并发重复；同键非 FAILED 跳过重派。
  消费侧 RUNNING/FAILED 回写与租约回收已在 P1-MQ-02 落地。
  验证：同 incident 重复 sendDiagnosisTask 仅一行任务。
  Effort: S

- [x] **P1-CP-09** 聚合修正：✅ commit 46e7cab。精确匹配
  `findByServiceAndStatusInAndStartedAtAfter`（状态/时间窗下推 SQL，不再 containing
  误聚合）；incident 并发创建竞态以 ponytail 注记（fingerprint 去重已挡同指纹重复，
  同服务不同告警并发窗口窄，根治需 partial unique index——遗留）。
  验证：并发 50 条同类告警 ≤1 incident；"api" 不聚合进 "api-gateway"。
  Effort: S-M

- [x] **P1-CP-10** 乐观锁与状态机强制：✅ Incident @Version（V6 迁移）+ 乐观锁冲突
  统一映射 409；transitionIfAllowed 非法流转抛 409（同状态视为幂等重放放行）。
  链 IT 断言 DETECTED→RESOLVED 非法流转 409。
  验证：并发 transition 仅一个成功；非法流转 409。
  Effort: S

- [x] **P1-CP-11** 事务边界：✅ auto-remediation/approve 执行移到事务 afterCommit +
  **REQUIRES_NEW 事务模板**（关键坑：afterCommit 里 REQUIRED 写会进已提交的死事务
  静默丢失——IT 实测 executor HTTP 200 但状态不落，修复后 40/40 绿）；
  rootCause @NotNull→@NotBlank。
  验证：HTTP 成功但后续事务失败 → remediation 行仍存在且状态明确。
  Effort: M

- [x] **P1-CP-12** 审批语义补全：✅ expiresAt（V4 迁移 + create() TTL 1h 可配
  `aisre.approval.ttl-seconds`，过期 decide→409）；REJECT 推进 WAITING_APPROVAL→
  ROOT_CAUSE_FOUND（状态机放开该转换）并审计；decidedBy 缺省取 JWT sub
  （ApprovalController 解析）；同 incident+action 复用 PENDING（AgentResultService）。
  链 IT 新增 Order(3) REJECT 回退断言。
  验证：过期 decide 409；REJECT 后状态断言。
  Effort: S-M

- [x] **P1-CP-14** AuthZ 收紧：✅ 读端点 ≥VIEWER（Bearer JWT 或 agent token）；
  alerts webhook 加共享 secret（X-Webhook-Token，未配置放行+WARN，compose 与
  alertmanager.yml 同值）；actuator 移独立管理端口 8085（内部）。前端/agent-runtime
  GET 均已带凭据；stream SSE 放行（EventSource 无法带头）。
  验证：端点×角色矩阵测试。
  Effort: M

- [x] **P1-CP-15** Redis 降级策略：✅ commit 46e7cab。putIfAbsent/delete try/catch →
  fail-open + WARN（告警管道不再因 redis 故障 500）；firstSeen=false 时只落 alert 行
  挂活跃 incident，不重复计数/摘要/触发任务（链 IT 断言重放后 alertCount==1）。
  验证：Redis 停止时 POST /alerts 仍 202；重复告警 alertCount 不虚增。
  Effort: S

- [x] **P1-CP-16+18** CP 全链路 SLF4J 日志 + DTO validation（`spring-boot-starter-validation`、@NotBlank、Map.of null 安全）。
  ✅ 已完成（commit 2ebee47）：关键路径日志（告警摄入/诊断保存与幂等跳过/task 生命周期/修复执行）
  + GlobalExceptionHandler 补 validation 400 与兜底 500 日志；5 个写 DTO 加约束 + 控制器 @Valid；
  DtoValidationTest(4)，Java 31 OK（后续 36 OK）。
  验证：修复失败有 warn/error 日志含堆栈；缺字段请求 400。
  Effort: S

- [x] **P1-CP-17** schema 单轨：✅ ddl-auto=validate；抓出并修复：flyway 原只在
  docker profile（IT 无 flyway、agent_step 一直靠 ddl-auto 建）→ flyway 提升为
  主依赖，IT 走真实迁移路径；CI 新增 java-integration job（testcontainers +
  validate 启动即断言实体↔Flyway 对齐）。
  验证：Testcontainers PG + Flyway 后以 validate 启动无 diff。
  Effort: S

- [x] **P1-AR-04** LLM 重试接线：✅ `_build_runner` 包 RetryLLMProvider（此前只定义
  未接线）；429 尊重 Retry-After（封顶 10s，超上限直接上抛）、5xx/网络短退避、
  4xx 不重试；可配 LLM_MAX_RETRIES/LLM_RETRY_DELAY_SECONDS；单测 5 个。
  验证：接线断言（失败 2 次后成功，调用计数=3）。
  Effort: S

- [x] **P1-AR-05** 消费提交语义：✅ submit 失败重试 N 次后**上抛**（不再吞掉）→
  任务 fail 上报、complete 不调；mark_processed 保持 complete 成功后执行；
  幂等文件写改 tmp+原子 rename。单测 2 个。
  验证：submit 抛错 → 任务保持 QUEUED；重复投递仅一次 submit。
  Effort: S-M

- [x] **P1-AR-06** 确定性 Verification：✅ 观察窗 VERIFICATION_OBSERV_WINDOW_SECONDS
  （默认 60s，不计入预算）→ Prometheus 采 error_rate/p95 → 阈值判定
  （VERIFICATION_MAX_ERROR_RATE / VERIFICATION_MAX_P95_SECONDS）→ LLM 仅写解释、
  无恢复决定权；RECOVERED 必带 sli 证据 + VerificationResult.sli 字段；
  Prom 无数据 → UNKNOWN 兜底。单测 10 个（commit 473fda0）。
  验证：故障未真正恢复时验证不判 RECOVERED（注入持续故障的测试）。
  Effort: M
  依赖：P0-02（查询对的服务）

- [x] **P1-AR-07** 工具超时强制：✅ Tool.call 线程池 future.result(timeout=
  spec.timeout_seconds)（wait=False，超时后不陪卡死线程等完）；TIMEOUT 状态照旧
  透出给 agent。单测 2 个（慢工具 0.2s 截断 / 快工具不受影响）。
  验证：卡死工具在 timeout 内返回 TIMEOUT 状态。
  Effort: S

- [x] **P1-AR-08** prompt 注入防护：✅ system 声明「工具/检索内容是数据」；
  证据/工具输出用 <evidence> 包裹；可疑指令句式（ignore previous / you are now /
  rm -rf / DROP TABLE / curl|sh 等）标注 [possible_injection]；诊断 prompt 头部同声明。
  单测 3 个（commit 473fda0）。
  验证：含 "ignore previous instructions" 的 runbook 检索后结论不受影响的测试。
  Effort: S

- [x] **P1-MQ-01** 消费端决策：✅ 方案 (a)——生产路径确认为控制面轮询消费
  （compose AUTO_CONSUME=true → consumer_loop；mq_consumer.py 从未被 main.py 接线），
  已在模块头标注 EXPERIMENTAL 并注明启用前提（毒消息/DLQ 语义与轮询对齐）。
  验证：(a) 文档与架构图一致；(b) kill 消费者 → 消息重投 → 处理成功（幂等）。
  Effort: S(a)/L(b)

- [x] **P1-MQ-02** 任务 claim/lease：`UPDATE ... SET status='RUNNING', claimed_by, claimed_at WHERE status='QUEUED'` 条件更新 + 超时回收扫描；消费端带 taskId。
  ✅ 已完成（commit 51d4413）：claimTask 原子抢占 + reclaimExpiredLeases 定时回收（lease 600s 可配）
  + /tasks/{id}/claim|complete|fail 三端点 + V3 迁移；Python 消费端先 claim 再诊断、失败上报 fail；
  e2e fake CP 同步实现。测试：test_claim_prevents_duplicate_consumption。
  验证：两消费者并发领取同一任务仅一成功；租约超时被回收重发。
  Effort: M

- [x] **P1-MQ-03** 毒消息与 DLQ：✅ agent_task.attempts（V7 迁移）——租约回收时
  重试 +1，达上限（aisre.task.max-attempts，默认 16）转 DEAD（DLQ 等价物，可查询）
  + TASK_POISONED 审计 + ERROR 日志（attempts==max 仅首次审计，不重复）。
  幂等存储：CP 侧唯一索引 idempotency_key + claim 条件更新即 DB 级幂等（agent-runtime
  文件存储仅为本地缓存）。链 IT Order(4) 验证回收→DEAD 全路径。41/41 绿。
  验证：构造必失败消息 → 终态 FAILED + DLQ 记录 + 告警事件。
  Effort: M

- [x] **P1-FI-03** 告警规则与故障对齐：✅ 7 条规则 expr 逐一经 Prometheus API 验证引用
  真实非空序列（HighErrorRate/HighLatency/ServiceDown/HighCPU/HighMemory/
  RedisPoolHigh/DatabasePoolHigh）；HighCPU 阈值 0.8→0.7（busy-loop 实测 0.79-0.83
  贴边易漏报）。故障类型→规则映射：cpu_saturation→HighCPU；redis_pool→HighErrorRate
  （真实 503）；memory_leak→HighMemory；thread_pool→HighLatency；slow_sql/mq_backlog
  需先落对应真实故障源（slow_sql 无 pg 慢查询注入、rocketmq-exporter 不可得，见 FI-06 注记）。
  验证：注入每个 REAL 故障后有对应告警触发。
  Effort: S

- [x] **P1-FI-04** 日志进 Loki：✅ promtail docker_sd 容器（`com.docker.compose.service` → service 标签，
  Loki 摄入限放宽至 30/60MB 防回填 429）。验证：`query_logs` 实测返回带 traceId 的真实业务
  日志行；`{service="payment-service"}` 可查（含 ERROR 级 RedisConnectionFailureException 行）。
  commit 7c5c5f9。Effort: S-M

- [x] **P1-FI-05** 指标管道：✅ 全部完成。
  一期（commit d09ca46）：prometheus `--web.enable-remote-write-receiver`，
  application_ready_time 等 pushed 指标入 Prometheus。
  二期：demo services shared/observability.py 加 OTel MeterProvider
  （OTLPMetricExporter → collector /v1/metrics，15s 间隔）；验证：demo 侧
  `http_server_duration_milliseconds_*` 等 OTel 族指标真实入 Prometheus
  （与 prometheus_client 的 `http_request_duration_seconds_*` 两族并存），collector 无 404。

- [x] **P1-FI-06** exporter 或删规则：✅ redis-exporter + postgres-exporter 落真
  （redis_connected_clients=3、pg backends=12 真实入 Prometheus，RedisPoolHigh 保持、
  DatabasePoolHigh 改 `sum(pg_stat_database_numbackends) > 50`）；RocketMQLagHigh 删除
  （exporter 镜像在可达源均不可得，无数据源规则=虚假可观测；恢复需先落 exporter）。
  commit 7c5c5f9。验证：规则 expr 查询非空 ✅。Effort: S

- [x] **P1-T-01** 删 `tests/test_extended.py` + `generate_extended_tests.py`：✅ commit abce41c，
  268→58 用例（真实质量用例全保留，OK 1 skip）；文档计数以 unittest 实际输出为准。
  验证：unittest 数量 = 真实用例数 ✅。Effort: S

- [x] **P1-T-02** Java 核心链路测试：✅ ControlPlaneChainTest（commit 82f59ff）
  @SpringBootTest + Testcontainers(POSTGRES+redis) + MockWebServer 覆盖
  ingest→dedup(重放 duplicate=true)→incident→诊断回调→LOW 风险 auto-policy 自动批准
  →remediation 断言(/api/k8s + X-Execution-Token)→VERIFYING→verification(RECOVERED)
  →RESOLVED；HIGH 风险人工审批链 + AuthInterceptor 矩阵（无/坏 token 401、viewer 403、
  admin 200、agent 错 token 401）。39/39 全绿（37+2）。
  顺带修复：decide() 终态归一 APPROVED/REJECTED（原与 auto-policy 两种约定）。
  Effort: M-L

- [x] **P1-CI-01** CI 补 lint 与前端构建：✅ ruff check agent-runtime + web build job
  已入 CI（FE-01 定版后 npm ci 可复现）。验证：CI 步骤含 ruff 与 web build ✅。
  Effort: S

- [x] **P1-FE-01** 前端定版：✅ 用户拍板保留 React(vite) 轨（commit 7a8543d）。
  删静态轨（旧 index.html/app.js），React 入口改标准 index.html（原
  index.react.html 非标准名导致 vite 永远构建静态轨）；Dockerfile `npm ci`
  （lock 重生成同步）+ npmmirror；compose frontend 改构建镜像。
  验证：`docker compose build frontend` 产物 /assets/index-*.js 200、/api 代理正常 ✅。
  Effort: S

- [x] **P1-DOC-04/05/06/07** 文档与代码对齐：✅ architecture.md 重绘（轮询主链路 +
  MQ outbox 标注 EXPERIMENTAL、REJECT→ROOT_CAUSE_FOUND、任务生命周期含 DEAD、
  API 表带鉴权列；audit DOC-04 的工具 URL 未注入问题 compose 已修——`*_TOOL_URL`
  指向 tool-server）；security.md 重写（静态 token 可重放、脱敏死代码、SSE 公开、
  /faults 开放等如实披露）；production-readiness-audit.md 按现状重写
  （RBAC/Flyway/审批 token/AM 链路从 ❌/🟡 转 ✅，关键风险表更新）。
  验证：逐条对照 audit 的 DOC 总表无 FALSE/PARTIAL 未披露项。
  Effort: S-M

# P2

- [x] **P2-CP-19** SSE 心跳+onError+并行发送：✅ 15s heartbeat（防中间层断链）+
  onError/onTimeout/onCompletion 三清理；单实例进程内广播（多实例 Redis pub/sub 注释已留）。
- [x] **P2-CP-20** findAll 扫描改派生查询：✅ list(null)→findAllByOrderByStartedAtDesc；
  dashboard/summary→countByStatus/countByStatusIn 下推 DB（恢复时长仍取已解决行）。
- [x] **P2-CP-21** 健康检查统一：✅ /health 并行探测 DB+Redis（CompletableFuture，
  10s 超时）→ ok/degraded；management.endpoint.health.probes.enabled=true
  （/actuator/health/{liveness,readiness}，管理端口 8085）。
- [x] **P2-CP-22** 死代码清理：✅ 删 Runbook/EvaluationCase 实体+repo（V8 drop 表）、
  Incident.report、updateRootCause、TimeoutLLMProvider 假超时包装（超时由 httpx +
  RetryLLMProvider 边界负责）。教训：删实体后必须 clean 重编译（增量编译残留 stale
  class 会骗过 schema validate）。
- [x] **P2-CP-23** Agent 链路关联：✅ diagnosis/verification 均带 taskId →
  - 追加发现（真实 E2E）：consume_once 轮询 GET 未带 agent token（P1-CP-14 读门控
    后一直 401，循环 `except: pass` 静默吞错）→ 已修复 + WARN 日志；另发现手工
    告警（无 instance/pod 标签）resource=null 被 DB 拒收 → AlertmanagerAdapter
    resource 兜底（instance→pod→resource→service）。均实测：incident 77 全链路
    （fault→alert→轮询诊断→DB 落库 task_id/risk_level/query/time_range）。
  Evidence/ToolCall 落库不再断链（原 null）；riskLevel 来源=agent 端 ToolSpec
  （策略工件，执行时盖章 `call.risk_level=spec.risk_level`），CP 侧缺省 READ_ONLY。
- [ ] **P2-CP-24** 随 P1-T-02 覆盖。
- [x] **P2-AR-09** Evidence 字段扩展：✅ agent Evidence 加 query/time_range
  （查询类工具自动提取 `[5m]` 类窗口），payload + CP V9 迁移（evidence.query/time_range），
  timestamp 由 DTO 可选携带；DiagnosisResult.status 语义三分：ROOT_CAUSE_FOUND /
  UNKNOWN（LLM 降级）/ **TIMEOUT**（预算耗尽，不再伪装 UNKNOWN，测试同步更新）。
- [ ] **P2-AR-10** Planner 与 function calling 合并决策（随 AR-02 中期方案）。
- [ ] **P2-AR-11** mcp_client 删除或接线。
- [ ] **P2-FI-07** chaos YAML 删除或标注 experimental（K8s 实测后再启用）。
- [ ] **P2-FI-08** self-monitoring：agent-runtime/tool-server `/metrics`（prometheus_client）+ scrape job + up 告警 + ≥1 张 Grafana dashboard；补平台自身指标（诊断时延、tool 失败率、任务积压、DB 池）。
  验证：Grafana 有平台面板；停 agent-runtime 有 ServiceDown 告警。
- [ ] **P2-FI-09** SLO recording rules（availability/p95/error rate）+ 最小 error budget 面板。
- [ ] **P2-FI-10** 评估期望证据与真实机制对齐（随 P0-08）。
- [ ] **P2-T-04** 集成测试加迁移+仓库冒烟；CI 加 `-Pintegration verify`（services: docker）。
- [ ] **P2-T-05** contract test 对真 CP 跑（Testcontainers 起真 CP）。
- [ ] **P2-FE-02** Playwright 冒烟（3-5 用例：列表/详情/审批 401）。
- [ ] **P2-FE-03** EventSource 去手动 close；统一 fetch 错误+401 处理。
- [ ] **P2-E2E-01** local_e2e_runner 更名"契约冒烟"；文档定位改写。
- [ ] **P2-BM-02** agent-benchmark `--url/--output`、失败处理、阈值；结果 JSON 入仓。
- [ ] **P2-BM-03** qps 改 wall-time；删/换 sse-stream；k6 alert 阈值结论如实记录。
- [ ] **P2-CI-02** nightly integration job：compose up + RUN_E2E=1 + k6 smoke + run_evaluation。
- [ ] **P2-CI-03** 首次 push 后以真实 CI 运行记录更新文档。
- [ ] **P2-DOC-08/09/10** 测试计数统一、故障表/Tool 说明更新、README Future Work/limitations/runbooks 清理。
- [ ] **P2-GIT-02** 调试产物归档（`archive/` 或删除）+ ignore。
- [ ] **P2-K8S-01** K8s 修复与实测：default-deny 加 DNS egress；补 tool-server/frontend Deployment；数据层 manifest（或明确 compose-only）；镜像 pin；liveness/securityContext；kind/minikube 部署演练并归档。
  验证：kind 部署后全链路 smoke 通过。

# P3

- [ ] **P3-CP-25** 状态枚举化；rocketmq.* 死配置清理；pom docker profile 说明。
- [ ] **P3-FI-11** redis instrumentation span；access log traceId；gateway 生成 X-Request-Id。
- [ ] **P3-FI-12** AM 分组与标签粒度（resource={{ $labels.service }}）。
- [ ] **P3-T-06** 真实 E2E 断言 root_cause ∈ 期望集合；时长改比例阈值。
- [ ] **P3-CI-04** 缓存/Python 版本统一/run_all_local_tests 去重。
- [ ] **P3-CI-05** gitleaks（或 scan-secrets.ps1）+ kubeconform 接 CI。
- [ ] **P3-FE-04** API base 注入点；timeline 用真实 createdAt。
- [ ] **P3-DOC-11** 轮换 .env 中的真实 API key。
- [ ] **P3-DOC-12** api-contract 补 2 端点；api.md 方向修正；configuration.md 默认值统一。
- [ ] **P3-EV-01** case 模板多样化（每 fault ≥5 表述 + 服务/严重度扰动）。
- [ ] **P3-备份演练** backup/restore 脚本自动化演练（compose 环境即可）并归档记录。

---

## 完成定义（DoD）

每个 P0/P1 项勾选前必须：① 有对应测试或可复现验证命令；② `git status`/`diff` 仅含本项修改；③ audit 文档中对应 finding 状态更新（若该 finding 因此关闭）；④ 相关文档（README/architecture/implemented-features）同步修正，不允许文档再次领先现实。

## 建议执行顺序（2 周）

第 1-2 天：P0-12 → P0-01 → P0-02 → P0-06
第 3-5 天：P0-03（Evaluation 重构）
第 6-7 天：P0-05 + P1-MQ-02 → P0-04
第 8 天：P1-CP-16/18 → P0-11 + DOC 即时更正
第 9-10 天：P0-07 → P1-FI-04 → P1-FE-01 → P1-CI-01
第 2 周起按 Stage 3-6 继续（见 audit Roadmap）。
