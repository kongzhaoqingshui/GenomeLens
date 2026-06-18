# GUI Git 工作流

> 本文件专门约束 `gui/` 子项目的 Git 协作方式。未提及的事项遵循项目级 `docs/开发手册/协作开发方案.md` 与 `docs/开发手册/开发规范.md`。

---

## 1. 分支模型

GUI 子项目沿用项目级 GitHub Flow（简化版）：

```text
main  ──────────────────────────────────────►
       \
        gui/feature/xxx  ──PR──►  main
       /
        gui/fix/xxx      ──PR──►  main
       /
        gui/docs/xxx     ──PR──►  main
```

- 只保留一条长期分支 **`main`**。
- 所有 GUI 改动从 `main` 切出短生命周期分支。
- 通过 Pull Request 合并回 `main`，禁止直接 `git push` 到 `main`。

---

## 2. 分支命名规范

| 类型 | 前缀 | 示例 |
|------|------|------|
| 新功能 | `gui/feature/` | `gui/feature/project-list-page` |
| 缺陷修复 | `gui/fix/` | `gui/fix/progress-bar-shimmer` |
| 文档/非代码 | `gui/docs/` | `gui/docs/tauri-setup` |
| 重构 | `gui/refactor/` | `gui/refactor/signal-bus-adapter` |

命名规则：

- 全部小写，单词用 `-` 连接。
- 尽量包含 issue 编号：`gui/feature/42-dark-mode`。
- 与平台/引擎改动区分：GUI 分支必须以 `gui/` 开头，便于过滤与权限管理。

---

## 3. 提交信息规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)，scope 统一为 `gui`：

```text
type(gui): 简短描述

[可选详细说明]

[可选关联 issue]
```

常用类型：

- `feat(gui)`：新增界面或交互
- `fix(gui)`：修复 UI 或 Tauri 侧问题
- `docs(gui)`：GUI 文档更新
- `style(gui)`：不影响逻辑的格式、样式调整
- `refactor(gui)`：重构组件、状态管理
- `test(gui)`：前端或 Tauri 测试
- `chore(gui)`：依赖升级、构建脚本调整

示例：

```text
feat(gui): add project list page with empty state

- Add ProjectList, ProjectCard components
- Connect to list_projects Tauri command

Closes #12
```

---

## 4. 开发流程

### 4.1 开始新任务

```bash
# 1. 同步本地 main
git checkout main
git pull origin main

# 2. 切出 GUI 功能分支
git checkout -b gui/feature/xxx

# 3. 开发、提交
git add ...
git commit -m "feat(gui): ..."

# 4. 推送到远程
git push -u origin gui/feature/xxx
```

### 4.2 创建 PR

1. 在 GitHub 上从 `gui/feature/xxx` 向 `main` 发起 PR。
2. PR 标题：`feat(gui): 简短描述`。
3. PR 描述说明：
   - 改动动机
   - 主要变更点
   - 如何验证 / 测试命令
   - 截图或 GIF（UI 改动强烈建议）
   - 关联 issue

### 4.3 代码审查

- 至少 1 人 approval 后方可合并。
- 审查关注点：
  - UI 是否符合 `GUI视觉与交互风格指南.md`
  - Tauri Command 是否安全（权限最小化）
  - 是否把业务逻辑泄漏到前端
  - 前端组件是否可复用、可测试
  - 是否有新依赖未声明

### 4.4 合并

- 优先使用 **Squash and merge**，保持 `main` 提交历史线性清晰。
- 合并后删除远程功能分支：

```bash
git push origin --delete gui/feature/xxx
```

---

## 5. 与平台/引擎改动的协同

- GUI 分支**不应同时修改** `platform/` 或 `engines/jcvi/` 的核心逻辑。
- 若 GUI 需要平台新接口，应先在主仓库以非 GUI 分支完成平台改动并合并到 `main`，再切 GUI 分支基于最新 `main` 开发。
- 每周同步会检查 `main` 是否有影响 GUI 的接口变更（manifest / summary / CLI 输出）。

---

## 6. CI 与自动化检查

当前 GUI 先行阶段，建议在 PR 中手动验证：

```powershell
cd gui/tauri
pnpm install
pnpm lint
pnpm typecheck
pnpm test
pnpm tauri build --debug
```

未来可在 `.github/workflows/` 增加轻量 CI：

```yaml
# .github/workflows/gui-ci.yml 示例
name: GUI CI
on:
  pull_request:
    paths:
      - 'gui/**'
jobs:
  lint-and-test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: cd gui/tauri && pnpm install
      - run: cd gui/tauri && pnpm lint
      - run: cd gui/tauri && pnpm typecheck
      - run: cd gui/tauri && pnpm test
```

---

## 7. 不发布约束

- GUI 先行阶段**不构建正式安装包**。
- 本地只使用 `pnpm tauri dev` 或 `pnpm tauri build --debug`。
- 不推送 `gui/tauri/src-tauri/target/` 或 `gui/tauri/dist/` 到仓库。
- 不创建 GUI 专属 release tag；GUI 能力随主版本（如 v1.1.0）统一发布。

---

## 8. 常用命令速查

```bash
# 创建并切换分支
git checkout -b gui/feature/xxx

# 提交
git commit -m "feat(gui): add xxx"

# 推送
git push -u origin gui/feature/xxx

# 同步 main
git checkout main
git pull origin main
git checkout gui/feature/xxx
git rebase main

# 删除本地/远程已合并分支
git branch -d gui/feature/xxx
git push origin --delete gui/feature/xxx
```

---

## 9. 检查清单

提交 GUI PR 前确认：

- [ ] 分支基于最新 `origin/main`。
- [ ] 分支名以 `gui/` 开头。
- [ ] 提交信息使用 `type(gui): ...` 格式。
- [ ] `pnpm lint` 与 `pnpm typecheck` 通过。
- [ ] 相关组件/命令测试通过。
- [ ] UI 改动附有截图或 GIF。
- [ ] 文档已同步更新（gui/docs/ 或 docs/开发手册/）。
- [ ] 合并后删除远程分支。

---

## 10. 参考

- `docs/开发手册/协作开发方案.md`
- `docs/开发手册/开发规范.md`
- `./开发计划.md`
- `./视觉与交互风格指南.md`
