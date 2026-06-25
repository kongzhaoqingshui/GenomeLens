# gui/ — 图形界面层

本目录包含 GenomeLens 桌面 GUI 实现，定位为 **Windows / macOS 用户交互外壳**，而不是新的业务核心。

## 当前状态（1.0.0-preview-1）

- `gui/tauri/`：第一个先行 GUI 版本 **JCVI meow**，基于 Tauri v2 + React 18 构建，版本号 `1.0.0-preview-1`。
- `gui/docs/`：GUI 本地开发文档索引（开发计划、风格指南、Git 工作流、构建说明）。
- `gui/demo-data/`：GUI 开发期示例数据。

## 边界（重要）

GUI 层负责：项目浏览、任务创建、参数表单、运行进度、结果资产浏览、图件预览、Agent 对话入口、设置与环境诊断。

GUI 层**不负责**：

- 实现分析算法。
- 持有平台核心业务规则。
- 单独维护一套与 CLI 不一致的任务协议。

GUI 通过本地 API / 命令桥接 / sidecar 与平台核心（`platform/`）通信，目标是复用同一套 `WorkflowRequest v3` 任务协议，不得把核心逻辑迁入前端。当前 GUI 源码仍有旧请求草案模型遗留，后续开发应优先按 `docs/开发手册/GUI先行开发/开发计划.md` 完成协议迁移。

## 开发入口

使用根目录构建助手运行完整本地 GUI 验证流：

```powershell
.\scripts\build_gui.ps1
```

默认流程会安装 GUI 依赖，运行前端 lint/typecheck/tests/web build，再运行 Tauri Rust `cargo check` 与 `cargo clippy -- -D warnings`。

要构建真正的桌面应用并把可运行 GUI 入口发布到 `app/JCVI-meow-gui/`：

```powershell
.\scripts\build_gui.ps1 -TauriBuild
```

可运行应用入口会被复制到 `app/JCVI-meow-gui/JCVI-meow.exe`。仅在需要 debug-profile GUI 构建时使用 `-DebugBundle`。

更详细的 Tauri 本地命令见 [`gui/tauri/README.md`](tauri/README.md)。
本地开发计划、分工与视觉规范见 [`gui/docs/README.md`](docs/README.md) 与 `docs/开发手册/GUI先行开发/`。
