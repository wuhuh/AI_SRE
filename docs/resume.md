# 简历素材

## 项目简介

设计并实现 AI SRE 智能故障诊断与自愈平台，基于 Multi-Agent、RAG、Tool Calling 与 OpenTelemetry，打通“告警接入 → 诊断 → 人工审批 → 自动修复 → 恢复验证 → Incident Report”的完整闭环。系统包含 Spring Boot Control Plane、Python Agent Runtime、Tool Gateway、可观测性栈和 200 个故障评测用例。

## 简历 Bullet

1. 设计并实现 AI SRE 智能故障诊断平台，包含 Control Plane、Agent Runtime、Tool Gateway、RAG 和可观测性系统，支持从真实告警到自动恢复验证的完整流程。

2. 构建 Python Multi-Agent Runtime，实现 Planner / Diagnostic / Verification 三阶段诊断，支持 Prometheus、Loki、Trace、K8s、Redis、DB 等 Tool Calling，并基于 Evidence 持久化保证结论可验证。

3. 实现 200 个故障评测用例和自动 Evaluation Runner，覆盖 Redis 连接池、慢 SQL、CPU 饱和、内存泄漏、RocketMQ 堆积等 10 类故障；本地 E2E 已验证 Redis 和慢 SQL 故障从注入到恢复的完整闭环。

4. 设计 Tool 安全体系，包含 READ_ONLY / HIGH_RISK 分级、参数校验、限流、JWT 鉴权、人工审批与审计日志，并对高危修复操作提供 Human-in-the-loop 控制。