# GUI 先行开发计划

> 本计划定义 GenomeLens 桌面 GUI（Tauri）的先行开发节奏与三人分工。>
> 目标：在 v1.0.0 核心功能稳定的同时，把 GUI 先行开发到“本地可运行、功能可演示”状态；> 不发布正式安装包，不进入 CI 发布流水线，只保证开发环境本地可用。

---

## 1. 目标与边界

### 1.1 目标

- 搭建 `gui/tauri/` 最小可运行骨架。
- 实现项目浏览、任务创建、运行进度、结果浏览、图件预览、环境诊断等核心界面。
- 通过 `platform/` 已有 CLI / `AnalysisRequest` 协议与后端通信，**不在 GUI 层重写业务逻辑**。
- 输出一套可持续演进的前端组件库、Tauri 命令层和数据流模式，为后续 macOS / Windows 正式交付打基础。

### 1.2 非目标

- 不发布 MSI / DMG / AppImage 等安装包。
- 不做自动更新、签名、应用商店上架。
- 不替代 CLI；CLI 仍是第一入口和自动化首选。
- 不在 GUI 里实现新的分析算法或引擎能力。

### 1.3 边界

GUI 层只负责：

- 项目浏览与任务创建
- 参数表单与模板选择
- 运行进度与日志展示
- 结果资产浏览与图件预览
- Agent 对话入口（占位）
- 本地设置与环境诊断

GUI 层**不负责**：

- 分析算法实现
- 平台核心业务规则
- 与 CLI 不一致的私有任务协议

---

## 2. 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 桌面宿主 | Tauri v2 | Rust 后端 + Web 前端，Windows 优先，macOS 可并行验证 |
| 前端框架 | React 18 + TypeScript | 团队生态成熟，组件化友好 |
| 样式 | Tailwind CSS + Headless UI | 统一设计系统，轻量。视觉规范见 `GUI视觉与交互风格指南.md` |
| 状态管理 | Zustand | 本地状态为主，避免过度设计 |
| 与后端通信 | Tauri Command + Sidecar | Rust 调用 `genomelens` 可执行文件 / Python 子进程 |
| 构建工具 | Vite（Tauri 内置） | 快速 HMR，开发体验好 |
| 包管理 | pnpm | 节省磁盘，monorepo 友好 |

---

## 3. 三人分工

### 成员 A：架构 / 后端集成负责人

**核心职责**：搭骨架、定协议、保打通。

- 初始化 `gui/tauri/` 项目结构（Rust + Vite + React）。
- 设计并实现 Rust 与 `platform` 的通信层：
  - Tauri Command（`analyze`、`check`、`list_projects`、`read_summary`、`read_log` 等）。
  - Sidecar / 子进程调用 `genomelens` 或 `jcvi-genomelens`。
  - 跨平台路径处理（Windows `.exe`、macOS app bundle 路径、开发时 PATH）。
- 定义前后端数据契约（JSON schema、事件流格式）。
- 项目持久化：工作区目录、最近项目列表、任务元数据存储（JSON / SQLite 轻量）。
- 环境诊断：复用 `check` 能力，向 GUI 暴露工具链状态。
- 负责本地开发脚本：`pnpm tauri dev`、Rust/Node 环境检查文档。

### 成员 B：前端界面 / 交互负责人

**核心职责**：出界面、保体验、统风格。

- 搭建前端工程：路由、布局、主题、组件库、图标。
- 实现主要页面：
  - 工作台首页 / 欢迎页
  - 项目列表与创建项目
  - 任务创建向导（选择方法、输入物种、参数表单）
  - 运行中页面（进度条、日志流、状态标签）
  - 结果页（摘要卡片、文件树、图件预览）
  - 设置页（环境、主题、路径）
- 设计系统：颜色、字体、间距、按钮/输入框/表单/模态/提示。严格遵循 `GUI视觉与交互风格指南.md` 中的冰蓝极简风格与动效规范。
- 响应式与可访问性：键盘导航、焦点管理、错误提示。
- 中文文案与术语统一（中英对照）。
- 编写前端组件测试（Vitest / React Testing Library）。

### 成员 C：业务 / 数据流负责人

**核心职责**：接业务、管状态、保正确。

- 把 `AnalysisRequest` JSON 协议映射为 GUI 表单模型与验证规则。
- 实现任务状态机与前端状态同步：
  - PENDING → VALIDATING → RUNNING → PARSING → FINALIZING → SUCCEEDED/FAILED。
  - 运行中实时读取 `run.log` / `engine_run_summary.json`。
- 结果资产解析：summary、figures、artifacts、pairwise_jobs、global_figures。
- 图件预览：图片懒加载、缩略图、放大查看、导出/打开目录。
- 错误处理：把平台错误码 / 异常转换为界面友好提示。
- 编写端到端冒烟测试（Tauri 官方驱动或最小脚本）。
- 维护 GUI 层的测试数据与最小 demo 工作流。

### 协作边界

| 工作项 | 主负责 | 协作者 |
|--------|--------|--------|
| Tauri 项目初始化 | A | B、C |
| 前后端数据契约 | A | C |
| 页面组件实现 | B | C |
| AnalysisRequest 表单映射 | C | B |
| 任务状态机 | C | A |
| 结果解析与预览 | C | B |
| 环境诊断 | A | C |
| 设计系统 | B | A、C |
| 文档与测试数据 | C | A、B |

---

## 4. 开发阶段

### Phase 0：骨架与本地开发环境（第 1 周）

目标：任何团队成员都能在本地 `pnpm tauri dev` 跑起空白窗口。

- [ ] A：初始化 `gui/tauri/`（Rust crate + Vite + React + TypeScript + Tailwind）。
- [ ] A：配置 Tauri 允许列表（fs、shell、dialog、notification、os）。
- [ ] A：编写 `pnpm tauri dev` / `pnpm tauri build --debug` 脚本与文档。
- [ ] B：搭建前端基础布局、路由、主题切换（light/dark）。
- [ ] C：准备最小 demo 工作区与 `AnalysisRequest` 样例。
- [ ] 全员：确认 `genomelens` conda 环境 + Rust + Node 可联动。

验收：

- `pnpm tauri dev` 在 Windows 本地正常启动。
- 能从 GUI 调用一个 Rust command 并返回版本号。

### Phase 1：项目与任务创建（第 2–3 周）

目标：用户可以在 GUI 里创建项目、选择方法、填写输入、生成请求。

- [ ] A：实现 `list_projects`、`create_project`、`delete_project` 等持久化命令。
- [ ] A：暴露 `analyze template mcscan` 输出到前端。
- [ ] B：实现项目列表页、创建项目弹窗、最近项目入口。
- [ ] B：实现任务创建向导（步骤条、物种输入卡片、参数表单）。
- [ ] C：把表单状态转换为 `AnalysisRequest`，做字段级验证。
- [ ] C：复用平台配置协议，读取/回写 `jcvi.config.json`。

验收：

- 可在 GUI 创建新项目。
- 填写物种与参数后，能生成与 CLI 一致的 `AnalysisRequest` JSON。
- 请求 JSON 可通过 `analyze run` 在 CLI 侧复现。

### Phase 2：运行与进度（第 4–5 周）

目标：用户在 GUI 里启动任务，并实时看到进度与日志。

- [ ] A：实现 `run_analysis` command，调用 `genomelens analyze run <request.json>` 子进程。
- [ ] A：设计事件流：stdout 解析、stderr 捕获、进程退出码、取消信号。
- [ ] B：实现运行中页面（进度条、状态标签、可折叠日志流、取消按钮）。
- [ ] C：把平台状态机映射到 GUI 状态，处理 `SignalBus` 事件或 tail `run.log`。
- [ ] C：失败时展示错误摘要与 `run.log` 最后 N 行。

验收：

- 从 GUI 启动的任务能在后台运行并写出 `run.log`。
- 进度条与状态标签随运行推进更新。
- 失败时界面能定位到关键错误信息。

### Phase 3：结果与预览（第 6–7 周）

目标：任务完成后，用户能在 GUI 浏览结果、预览图件。

- [ ] A：实现 `read_summary`、`list_artifacts`、`read_artifact` 命令。
- [ ] B：实现结果摘要卡片、文件树、图件网格预览。
- [ ] B：实现图片预览组件（点击放大、切换、复制路径、打开文件夹）。
- [ ] C：解析 `RunSummary`、`pairwise_jobs`、`global_figures`、`final_figures`。
- [ ] C：为结果资产生成缩略图列表与元数据。

验收：

- 成功任务的结果页能列出所有图件与关键中间文件。
- 点击图件可预览；右键/按钮可打开资源管理器。

### Phase 4：设置与诊断（第 8 周）

目标：用户能在 GUI 检查环境、配置路径、切换主题。

- [ ] A：把 `genomelens check` 结果暴露给 GUI。
- [ ] A：实现设置持久化（Tauri Store / 本地 JSON）。
- [ ] B：实现设置页与环境诊断页。
- [ ] C：把诊断结果与工具链定位策略映射为前端状态。
- [ ] C：Agent 对话入口占位（UI 面板，后端先 mock）。

验收：

- 设置页能保存并回显用户偏好。
- 环境诊断页展示 BLAST+、JCVI 引擎、ImageMagick 状态。

### Phase 5：打磨与测试（持续）

- [ ] B：统一 UI 细节、动画、空状态、加载态、错误态。
- [ ] C：补充端到端冒烟测试（最小 demo 工作流）。
- [ ] A：整理 `gui/tauri/README.md` 与 `docs/开发手册/GUI开发环境.md`。
- [ ] 全员：代码审查、文档同步、与 CLI 行为对齐。

---

## 5. 与平台核心的通信协议

### 5.1 推荐模式：Sidecar / 子进程

```text
GUI (React)
  ↓ Tauri Command
Rust Backend
  ↓ std::process::Command
platform CLI (genomelens)
  ↓ manifest / request.json
engine (jcvi-genomelens)
```

- 开发阶段直接调用本地 `genomelens` 可执行文件（conda 环境或 editable install）。
- 不引入 HTTP server，避免增加运行时复杂度。
- 未来若需要多客户端或远程调度，再考虑把 CLI 包装为本地 API server。

### 5.2 命令清单（V1 先行版）

| Tauri Command | 功能 |
|---------------|------|
| `get_version()` | 获取 platform / engine 版本 |
| `check_environment()` | 运行 `genomelens check` 并返回结构化结果 |
| `list_projects(workspace: string)` | 列出工作区项目 |
| `create_project(workspace, name)` | 创建项目目录 |
| `delete_project(workspace, name)` | 删除项目目录 |
| `get_template(method)` | 获取 `AnalysisRequest` 模板 |
| `run_analysis(request_path, outdir)` | 启动分析子进程 |
| `cancel_analysis()` | 向子进程发送终止信号 |
| `read_summary(outdir)` | 读取 `engine_run_summary.json` |
| `read_run_log(outdir)` | 读取 `run.log` 最新内容 |
| `list_artifacts(outdir)` | 扫描结果目录 |
| `open_path(path)` | 调用系统文件管理器 |

### 5.3 事件流

Rust 后端通过 Tauri `Event` 向前端推送：

```typescript
type GuiEvent =
  | { name: "analysis:stdout"; payload: { line: string } }
  | { name: "analysis:state"; payload: { state: string; progress: number } }
  | { name: "analysis:finished"; payload: { status: "SUCCEEDED" | "FAILED"; summary?: object } }
  | { name: "analysis:error"; payload: { message: string } };
```

---

## 6. 开发环境

### 6.1 必备依赖

- [Rust](https://rustup.rs/)（Tauri v2 要求）
- [Node.js](https://nodejs.org/) ≥ 18 + [pnpm](https://pnpm.io/)
- `genomelens` conda 环境（Python 3.12）
- `platform/` 与 `engines/jcvi/` 已做 editable install
- Windows 10/11；macOS 开发者可选验证

### 6.2 初始化命令

```powershell
cd gui/tauri
pnpm install
pnpm tauri dev
```

### 6.3 调试构建

```powershell
pnpm tauri build --debug
```

> 注意：`--debug` 构建产物仅用于本地调试，不用于分发。

---

## 7. 目录规划

```text
gui/
├── README.md                          # GUI 层总览（已存在）
└── tauri/
    ├── README.md                      # 开发环境说明
    ├── package.json
    ├── pnpm-lock.yaml
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── src/
    │   ├── main.tsx                   # 入口
    │   ├── App.tsx                    # 根组件
    │   ├── routes/                    # 页面路由
    │   ├── components/                # 通用组件
    │   ├── hooks/                     # 自定义 hooks
    │   ├── stores/                    # Zustand 状态
    │   ├── services/                  # Tauri command 封装
    │   ├── models/                    # TypeScript 类型
    │   └── styles/
    └── src-tauri/
        ├── Cargo.toml
        ├── tauri.conf.json
        └── src/
            ├── main.rs
            ├── commands/              # Tauri commands
            ├── sidecar/               # sidecar 调用封装
            ├── project/               # 项目持久化
            └── error.rs               # GUI 层错误类型
```

---

## 8. 不发布约束

- `tauri.conf.json` 中关闭自动更新、签名、 deep link 等发布相关能力。
- 不配置 CI 构建 MSI / DMG。
- `scripts/` 中不增加 GUI 发布脚本；只保留本地 dev / debug build 脚本。
- `docs/使用方法/` 里不公开 GUI 下载入口，只写“开发中，本地构建体验”。
- `.gitignore` 必须排除：
  - `gui/tauri/node_modules/`
  - `gui/tauri/dist/`
  - `gui/tauri/src-tauri/target/`

---

## 9. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Tauri v2 与 Windows 路径/权限踩坑 | 中 | A 先搭最小骨架，验证 sidecar 调用 |
| 平台 CLI 输出不稳定导致 GUI 解析失败 | 高 | 复用 `run.log` 与 `engine_run_summary.json`，少解析 stdout |
| 前端状态机与平台状态不同步 | 中 | C 主导状态映射，A 提供事件推送，B 负责展示 |
| 三人并行冲突 | 中 | 按 Phase 分主负责，契约文档先行，每日同步接口变化 |
| 偏离“GUI 不承载业务逻辑”边界 | 高 | Code Review 重点关注，平台协议变更必须同步 CLI 与 GUI |

---

## 10. 检查清单

### Phase 启动前

- [ ] 三人已安装 Rust + Node + conda + editable install。
- [ ] `gui/tauri/` 已初始化并能 `pnpm tauri dev`。
- [ ] 数据契约文档（本计划第 5 节）已确认。

### 每周同步会

- [ ] 上周完成的功能是否能在本地跑通最小 demo。
- [ ] 平台 CLI 是否有接口变化影响 GUI。
- [ ] 是否有新增 Tauri 权限需求。
- [ ] 是否有需要写入 `docs/更新计划/计划更新的内容.md` 的新条目。

### Phase 5 完成前

- [ ] GUI 可在本地从零 `pnpm tauri dev` 跑起。
- [ ] 最小 demo 工作流（双物种 BED+CDS）能完整跑完并预览图件。
- [ ] `ruff check`、`pytest platform`、`pytest engines/jcvi` 仍全部通过。
- [ ] 已新增 `docs/开发手册/GUI开发环境.md`。
- [ ] 已更新 `gui/README.md` 指向本计划与开发环境文档。

---

## 11. 参考资料

- `gui/README.md`
- `docs/开发手册/架构调整/最终架构目标.md`
- `docs/开发手册/架构调整/多平台兼容方案.md`
- `docs/开发手册/开发规范.md`
- `docs/更新计划/README.md`
- `platform/src/genomelens/analysis/request_models.py`
- `platform/src/genomelens/core/summary_models.py`
- `platform/src/genomelens/cli/main.py`
