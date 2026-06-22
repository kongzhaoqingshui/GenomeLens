# gui/ — 图形界面层

本目录包含 GenomeLens 桌面 GUI 实现，定位为 **Windows / macOS 用户交互外壳**，而不是新的业务核心。

## 当前状态（0.9.20）

- `gui/tauri/`：第一个先行 GUI 版本 **JCVI meow**，基于 Tauri v2 + React 18 构建，版本号 `0.9.20-preview.1`。
- `gui/docs/`：GUI 本地开发文档索引（开发计划、风格指南、Git 工作流、构建说明）。
- `gui/demo-data/`：GUI 开发期示例数据。

## 边界（重要）

GUI 层负责：项目浏览、任务创建、参数表单、运行进度、结果资产浏览、图件预览、Agent 对话入口、设置与环境诊断。

GUI 层**不负责**：

- 实现分析算法。
- 持有平台核心业务规则。
- 单独维护一套与 CLI 不一致的任务协议。

GUI 通过本地 API / 命令桥接 / sidecar 与平台核心（`platform/`）通信，复用同一套 `AnalysisRequest` 任务协议，不得把核心逻辑迁入前端。

## 开发入口

- 构建、运行、检查命令见 [`gui/tauri/README.md`](tauri/README.md)。
- 本地开发计划、分工与视觉规范见 [`gui/docs/README.md`](docs/README.md) 与 `docs/开发手册/GUI先行开发/`。
