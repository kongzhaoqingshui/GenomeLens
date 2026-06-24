# GUI 先行开发

本目录集中保存 GenomeLens 桌面 GUI（JCVI meow / Tauri）的先行开发资料。GUI 定位为平台交互外壳，不承载核心业务逻辑。

## 当前口径

- 平台现行任务协议是 `WorkflowRequest v2`。
- 平台执行层是 `WorkflowRequest -> ExecutionPlan -> engine manifest v3`。
- 结果摘要是 `RunSummary v3`，GUI 应优先消费 `artifact_index`、`child_runs`、`extensions`。
- GUI 当前源码仍有 `AnalysisRequest v1` 遗留，后续开发应先完成协议迁移，再继续扩展页面。

## 文档索引

- [开发计划](./开发计划.md) —— 当前状态、V2 迁移路线、Phase A-F、三人分工、验收标准。
- [前后端数据契约](./前后端数据契约.md) —— `WorkflowRequest v2`、Tauri Command、事件流、`RunSummary v3`、artifact 视图。
- [视觉与交互风格指南](./视觉与交互风格指南.md) —— 冰蓝色调、极简 Web 感、动效规范、首页布局。
- [JCVI meow 桌面体验设计增补](./JCVI喵桌面体验设计增补.md) —— 品牌、启动动画、中心能力环、Codex 风格工作台排版。
- [Git 工作流](./Git工作流.md) —— GUI 子项目分支命名、提交规范、PR 流程、合并策略。
- [构建与运行](./构建与运行.md) —— 环境依赖、初始化、本地调试构建、常见问题。

## 快速入口

```powershell
cd gui/tauri
pnpm install
pnpm tauri dev
```

完整本地验证优先使用根目录脚本：

```powershell
.\scripts\build_gui.ps1
```

详细说明参见 [构建与运行](./构建与运行.md)。

## 与本地 GUI 文档的关系

- `gui/docs/README.md` 是 GUI 开发者本地快速入口，指向本目录。
- 本目录下的文档是权威来源；`gui/docs/` 下不再保留副本，避免重复。

---

*本目录随 GUI 实现持续更新。*
