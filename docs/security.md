# Security

> 与代码对齐版（2026-09）。配 P0-05/06、P1-CP-12/14。

## 已实现

- **JWT 登录**（HS256；strict 模式 `AISRE_SECURITY_STRICT=true` 拒绝默认 secret/口令启动）
- **RBAC**：VIEWER / OPERATOR / ADMIN（口令支持 BCrypt 哈希，明文仅迁移期兼容）
- **鉴权拦截器**（AuthInterceptor）：
  - 读接口 ≥VIEWER（Bearer JWT，或 agent token 供 agent-runtime 只读查询）
  - 写接口（审批/transition）需 ADMIN/OPERATOR
  - agent 回调（diagnosis/verification/tasks）需 `X-Agent-Token`（未配置=**fail-closed**）
  - webhook（alerts）需 `X-Webhook-Token`（常量时间比较；未配置=放行+WARN，仅限本地开发）
  - 全部比较走 `MessageDigest.isEqual`（恒时）
- **审批安全**（P1-CP-12）：
  - 审批单 TTL 1h（`expiresAt`，过期 decide→409；V4 迁移存量补宽限）
  - 条件 UPDATE 消除并发双决（P1-CP-06）
  - decidedBy 取 JWT sub，全程审计
- **执行 token**（P0-04）：审批 APPROVE 生成 executionToken，tool-server 校验 `APPROVAL_TOKEN`
- **风险分级**：RiskPolicy READ_ONLY/LOW_RISK/HIGH_RISK；高风险必须人工审批
- **工具边界**：ToolSpec.allowed_principals + spec.timeout_seconds 强制超时（P1-AR-07）
- **注入防护**（P1-AR-08）：工具/检索输出视为数据，`<evidence>` 包裹 + 可疑指令 `[possible_injection]` 标注
- **隔离端口**：actuator（metrics/prometheus）独立 8085，不与业务端口同面
- **Schema 安全**：Flyway 单轨 + `ddl-auto=validate`（实体漂移启动即失败）
- Secret 全部经环境变量注入；`.env.example` 提供模板

## 已知风险（如实披露）

1. **静态共享 token 可重放**：agent token / webhook secret / approval token 均为长期
   静态值，泄露即可重放。生产应换 mTLS 或短期签名 token（见 limitations）。
2. **脱敏工具未接线**：`agent-runtime/app/masking.py` 有实现与单测，但无任何生产路径
   调用（死代码）——工具结果与证据**当前未脱敏**入 CP 库。
3. **SSE 流公开**：`/api/v1/stream` 无鉴权（EventSource 无法带 header）；如需收紧用
   query token 或改轮询。
4. **演示 fault 端点**：demo 服务的 `/faults` 开关在 compose 环境开放（生产必须关闭/网络隔离）。
5. **JWT 短期化未做**：登录 token 长期有效，无刷新/吊销机制。
6. **K8s 层缺失**：NetworkPolicy/RBAC/securityContext 未实测（P2-K8S-01）。
