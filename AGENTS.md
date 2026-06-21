# GenomeLens 子开发者 AI Agent 工作流

> 本文件约束被委派到 GenomeLens 项目执行具体开发任务的**子开发者 AI Agent**。
> 详细规则参考 `docs/开发手册/` 下的开发规范、协作方案与能力接入规则。
> 核心 AI 助理的权限与职责见仓库根目录 `CORE_AGENT.md`。

## 触发条件

用户提出以下类型请求时进入本流程：

- 新增功能 / 实现需求
- 修改、重构、重命名、调整 API
- 修复 bug / 处理 CI 或测试失败
- 审查 PR / 评估分支是否可合并
- 版本发布 / 文档同步

纯查询类任务（解释代码、查找文件等）可不进入本流程，但仍应保持代码与文档准确。

---

## 核心工作流

### 1. 理解需求并对齐文档

- 先阅读相关代码、测试和已有文档。
- 结合 `docs/更新计划/计划更新的内容.md` 判断本次改动属于哪个版本/方向。
- 如果涉及全新大方向，同步 `docs/项目介绍.md`、`docs/开发手册/架构调整/最终架构目标.md`。

### 2. 制定计划

- 每次迭代前写 `docs/开发手册/plans/<日期或版本>-<主题>.md`：
  - 复杂度等级、涉及模块、验收标准、技术债务、需同步的文档。
- 非平凡改动（多文件、架构选择、行为变更）使用 `EnterPlanMode`，用户批准后再实现。
- 需要用户拍板的事项，生成 `docs/开发手册/actions/<日期>-<主题>.md`，等待确认。

### 3. 执行开发

- 从最新 `origin/main` 切出分支：
  - `feature/xxx`、`fix/xxx`、`refactor/xxx`、`docs/xxx`、`hotfix/xxx`
- 提交信息使用 Conventional Commits：`type(scope): 描述`。
- 遵循 `docs/开发手册/开发规范.md` 与 `代码风格规范.md`。
- 新增 engine workflow 时，按 `能力接入规则.md` 的联动清单执行。

### 4. 验证

提交前或任务完成后运行：

```powershell
python -m ruff check platform/src platform/tests engines/jcvi/src/jcvi_genomelens engines/jcvi/tests integrations/haiant_plugin/src integrations/haiant_plugin/tests
python -m ruff format --check platform/src platform/tests engines/jcvi/src/jcvi_genomelens engines/jcvi/tests integrations/haiant_plugin/src integrations/haiant_plugin/tests
pyright platform/src/genomelens
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

### 5. 同步文档并交付

- 更新至少一类文档：用户文档、开发文档、更新计划。
- 发布版本时同步 `_version.py` 与 `docs/更新计划/更新日志.md`。
- 任务完成时向用户报告：改了什么、验证结果、文档更新、未决事项、后续建议。

---

## 关键文档速查

| 场景 | 参考文档 |
|---|---|
| 代码风格、类型、测试、发布 | `docs/开发手册/开发规范.md` |
| 分支、PR、提交规范 | `docs/开发手册/协作开发方案.md` |
| 新增 workflow 的联动要求 | `docs/开发手册/能力接入规则.md` |
| 更新计划、归档历史 | `docs/更新计划/计划更新的内容.md`、`.claude/skills/update-plan.md` |

---

## 红线

- **禁止直接 push 到 `main`**。
- **禁止擅自合并 PR**。
- **禁止批量删除文件或 API 而不生成 Action 文档**。
- **禁止跳过 lint / type check / test 直接宣布完成**。
- 同一问题补丁失败 ≥3 次，停止打补丁，生成 Action 文档建议重构或调整方案。

---

## PR 审查简要流程

1. `git fetch origin refs/pull/<n>/head:pr/<n>`
2. 检查 `git log main..pr/<n>` 与 `git diff --stat main..pr/<n>`
3. 重点看：是否回退已发布功能、是否破坏 shell-engine 契约、文档/测试是否同步
4. 给出结论：可合并 / 需修改 / 不可合并

---

*本文件随项目演进可修订。*
