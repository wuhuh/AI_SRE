# 当前环境限制

> 2026-09-07 更新：下列 Docker/Vite 限制为**历史快照**（当时开发会话的环境问题），
> 现已解决：compose 21 容器可复现运行、Testcontainers 链路 42/42 通过、
> Vite 构建正常。本文件保留供对照，实时差距见 docs/production-readiness-audit.md。

## Docker（历史，已解决）

当前开发会话无法访问 Docker daemon：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

因此以下事项无法在当前会话实际执行：

- 真实 Docker E2E
- Docker 环境 k6 API 压测
- Testcontainers 测试
- pgvector / RocketMQ 真实联调
- Chaos Mesh 真实实验

## React 构建

当前 Windows 环境执行 Vite 构建时：

```text
Error: spawn EPERM
    at ... esbuild ...
```

因此 React 生产构建无法在当前会话完成，需要在正常开发机或 Docker 容器中执行。

## 已完成的替代验证

- Python 单元测试 / Contract Test：通过
- 本地完整 E2E（Redis / 慢 SQL / CPU）：通过
- Auto Consumer 测试：通过
- MCP Client 测试：通过
- LLM 不稳定性测试：通过
- Baseline 对比：通过
- 本地 Agent Benchmark / API Load：已有真实数据