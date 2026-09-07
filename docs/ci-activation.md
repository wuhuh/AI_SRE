# CI 激活清单（P2-CI-03 前置就绪）

> 仓库当前无 remote（`git remote -v` 为空）。以下为 push 前后的一次性操作清单。

## Push 前（本地已就绪的部分）

CI 五个 job 的关键步骤已在本地等价实测通过（2026-09-07）：

| CI job / 步骤 | 本地等价验证 | 结果 |
| --- | --- | --- |
| java-build: `mvn test` | Testcontainers IT（同 mvn 3.9/temurin-17） | 42/42 |
| java-integration: `-Pintegration` | 同上 | 42/42 |
| python-lint: `ruff check agent-runtime` | 同命令 | All checks passed |
| python-test: `run_all_local_tests.py` | 同命令（含 unittest discover + 契约 smoke + 评测） | 全绿 |
| web-build: `npm ci && npm run build` | `npm run build`（12.96s）+ Playwright 5/5 | ✓ |
| secret-scan: gitleaks detect | v8.21.2 二进制同参数 | 0 leaks（2 误报已入 `.gitleaksignore`） |
| k8s-validate: kubeconform -strict | v0.6.7 二进制同参数 | 36/36 valid |
| docker-build: 各镜像 | `docker compose build` 全部成功（kind load 8 镜像） | ✓ |

无法本地验证（push 后自动有）：

- `nightly-integration` job（schedule cron 触发）——compose 全栈 + 真实 E2E + k6 + 评测冒烟，等首次夜间运行记录。

## 操作

```bash
# 1. 用户创建空 GitHub 仓库后：
git remote add origin git@github.com:<user>/<repo>.git
# 2. push（需用户明确授权；分支 ai/p0-stage1-fixes + main 历史）
git push -u origin ai/p0-stage1-fixes
# 3. 触发 CI（push 已触发 push job；PR 可另开）
# 4. 首夜后（次日 03:00 UTC cron）：查看 nightly-integration 运行记录
# 5. 以真实运行记录更新 docs/testing.md 的 CI 段（P2-CI-03 收尾）
```

## 注意

- `deploy/k8s/datastore.yaml` 使用 daocloud 镜像全名（本地网络受限环境）——
  GitHub Actions runner 直连 docker.io 无碍，kind 演练在 CI 外执行。
- k6 冒烟在 nightly 里跑 `grafana/k6:0.53.0`（Docker Hub 拉取，Actions 可达）。
