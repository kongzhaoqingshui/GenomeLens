# GUI 开发文档

本目录汇总 GUI 层（Tauri 桌面应用）的本地开发资料。GenomeLens 的 GUI 定位为平台交互外壳，不承载核心业务逻辑。

## 文档索引

权威 GUI 开发文档已集中到 `docs/开发手册/GUI先行开发/`：

- [开发计划](../../docs/开发手册/GUI先行开发/开发计划.md) —— 当前状态、V2 迁移路线、Phase A-F、三人分工、验收标准。
- [视觉与交互风格指南](../../docs/开发手册/GUI先行开发/视觉与交互风格指南.md) —— 冰蓝色调、极简 Web 感、动效规范、首页布局。
- [Git 工作流](../../docs/开发手册/GUI先行开发/Git工作流.md) —— GUI 子项目分支命名、提交规范、PR 流程、合并策略。
- [构建与运行](../../docs/开发手册/GUI先行开发/构建与运行.md) —— 环境依赖、初始化、本地调试构建、常见问题。
- [前后端数据契约](../../docs/开发手册/GUI先行开发/前后端数据契约.md) —— `WorkflowRequest v2`、Tauri Command、事件流、`RunSummary v3`、artifact 视图。

本目录只保留索引，不再保存副本。

## 快速入口

```powershell
cd gui/tauri
pnpm install
pnpm tauri dev
```

详细说明参见 [构建与运行](../../docs/开发手册/GUI先行开发/构建与运行.md)。

---

*本目录随 GUI 实现持续更新。*
