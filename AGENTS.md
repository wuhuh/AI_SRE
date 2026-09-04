# Git 开发工作流

你正在修改一个已经由 Git 管理的项目。

所有代码修改必须使用 Git 进行版本管理，并严格遵循以下流程。

## 1. 修改前检查

开始任何代码修改之前，必须执行：

```bash
git status
git branch --show-current
git log --oneline -5
```

目的：

- 确认当前分支；
- 检查是否存在用户尚未提交的修改；
- 理解最近的代码变更。

如果发现已有未提交修改：

- 不得执行 `git reset --hard`；
- 不得执行 `git checkout .`；
- 不得覆盖用户已有修改；
- 必须区分「已有修改」和「本次修改」。

------

## 2. 创建开发分支

除非用户明确要求直接修改当前分支，否则创建新的开发分支：

```bash
git switch -c ai/<task-name>
```

例如：

```bash
git switch -c ai/fix-memory-system
git switch -c ai/add-agent-router
git switch -c ai/refactor-hapfold-pipeline
```

禁止直接在 `main` / `master` 上进行大规模修改。

------

## 3. 修改前建立基线

修改代码之前，先理解当前状态。

根据项目情况运行已有测试：

```bash
pytest
```

或者：

```bash
mvn test
gradle test
npm test
```

如果完整测试成本过高，可以运行与当前任务相关的测试。

记录：

- 修改前哪些测试通过；
- 哪些测试原本就失败；
- 原有 warning / error。

不得把项目原本存在的问题误认为是本次修改引入的问题。

------

## 4. 小步修改

禁止一次性进行大量无关修改。

按照以下粒度开发：

```text
理解代码
↓
修改一个逻辑单元
↓
检查 diff
↓
运行测试
↓
继续下一步
```

每完成一个逻辑阶段后执行：

```bash
git diff
git diff --stat
```

确认：

- 是否修改了不应该修改的文件；
- 是否出现意外格式化；
- 是否删除了原有逻辑；
- 是否引入 debug 代码；
- 是否修改配置、依赖或接口。

------

## 5. 使用 Git 作为检查工具

开发过程中频繁使用：

```bash
git status
git diff
git diff --stat
```

如果已经 `git add`：

```bash
git diff --cached
```

需要理解某段代码历史时，可以使用：

```bash
git log -- <file>
git blame <file>
```

不得仅依赖当前文件内容判断设计意图。

------

## 6. 分阶段提交

每完成一个独立、可验证的功能后提交一次。

例如：

```bash
git add src/xxx tests/xxx
git commit -m "feat: add memory conflict detection"
```

Commit 应当遵循：

```text
feat: 新功能
fix: bug 修复
refactor: 重构
test: 测试
docs: 文档
chore: 工程调整
perf: 性能优化
```

例如：

```text
feat: add coordinator task scheduler
test: add scheduler failure cases
fix: prevent duplicate worker execution
refactor: simplify agent state management
```

一个 commit 应对应一个明确的逻辑修改。

不要把整个任务的所有修改压成一个巨大 commit。

------

## 7. 测试后才能提交最终版本

完成修改后必须运行相关测试。

至少执行：

```bash
git status
git diff
```

然后运行：

- 单元测试；
- 集成测试；
- lint；
- build；
- 与此次修改相关的实际运行测试。

如果存在测试失败：

必须判断：

```text
修改前就存在
还是
本次修改导致
```

不得为了让测试通过而直接删除测试。

------

## 8. 最终 Git 审查

任务完成后执行：

```bash
git status
git diff <base-branch>...HEAD
git log --oneline <base-branch>..HEAD
```

检查整个任务最终产生的所有修改。

重点检查：

1. 是否修改了任务之外的代码；
2. 是否意外删除功能；
3. 是否存在调试代码；
4. 是否存在硬编码路径；
5. 是否泄露 token / password / key；
6. 是否遗漏测试；
7. 是否存在无意义格式化；
8. 是否存在未追踪文件；
9. 是否遗漏配置或依赖文件。

------

## 9. 禁止危险 Git 操作

除非用户明确授权，不允许执行：

```bash
git reset --hard
git clean -fd
git checkout .
git restore .
git push --force
git push -f
git rebase
```

尤其禁止使用这些命令删除用户已有修改。

如果需要撤销本次修改，应优先精确撤销本次 AI 产生的变更，而不是重置整个工作区。

------

## 10. 不自动 push

默认情况下：

可以：

```text
branch
add
commit
diff
log
status
```

但不要自动执行：

```bash
git push
```

除非用户明确要求推送远程仓库。

------

## 11. 修改失败时使用 Git 回溯

如果某次修改导致测试或功能恶化：

首先查看：

```bash
git diff
git log --oneline
```

定位对应修改。

如果之前已经进行了阶段性 commit，应基于 Git 历史定位问题，而不是继续在错误代码上叠加 patch。

必要时回到最近一个确认正确的 commit，再重新实现。

禁止通过大量补丁不断掩盖之前错误的修改。

------

## 12. 最终报告

完成任务后向用户报告：

```text
完成内容
- ...

Git 分支
- ai/xxx

Commits
- abc123 feat: ...
- def456 test: ...

测试
- xxx tests passed

主要修改文件
- src/...
- tests/...

Git 状态
- clean / still contains xxx

未解决问题
- ...
```

如果没有 commit，也必须明确说明原因。

------

# 核心原则

始终把 Git 当作开发过程的一部分，而不仅仅是任务结束后的保存工具。

正确流程：

```text
git status
      ↓
理解现有代码
      ↓
建立 branch
      ↓
baseline test
      ↓
修改
      ↓
git diff
      ↓
test
      ↓
commit
      ↓
下一阶段修改
      ↓
git diff
      ↓
test
      ↓
commit
      ↓
最终整体 review
```

目标是确保任何一次 AI 修改：

- 可查看；
- 可审查；
- 可测试；
- 可定位；
- 可撤销；
- 不破坏用户已有工作。