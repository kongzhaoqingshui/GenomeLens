# GUI 数据契约与模型

本目录保存 JCVI meow（Tauri GUI）的数据模型、视图模型与前后端契约适配层。当前平台公开协议为 **WorkflowRequest v3** 与 **SubmoduleRequest v3**，结果摘要为 **RunSummary v3**。

## 当前文件说明

| 文件 | 用途 |
|---|---|
| `capability.ts` | 能力（Capability）元数据模型，区分 `one_stop` / `sub_module`，描述端口、参数与子模块分类。 |
| `workflow-request.ts` | 平台 `WorkflowRequest` 的 TypeScript 类型镜像，对应 `synteny` 一站式请求。 |
| `workflow-request-draft.ts` | GUI 本地表单状态 `WorkflowRequestDraft`、默认值构造器、与平台请求的互转适配器。 |
| `submodule-request.ts` | 平台 `SubmoduleRequest` 的 TypeScript 类型镜像，对应子模块请求。 |
| `submodule-request-draft.ts` | GUI 本地子模块草稿 `SubmoduleRequestDraft`、输入端口值适配与请求互转。 |
| `workbench-graph.ts` | 工作台节点编排图模型：任务节点 `TaskNode`、数据节点 `DataNode`、连线 `GraphEdge`、拓扑排序与端口兼容性。 |
| `workbench-preset.ts` | 任务预设持久化（`localStorage`），支持任务在画布上/画布外状态与图状态保存。 |
| `workbench-runner.ts` | 串行 DAG 运行引擎：按拓扑顺序执行节点、解析上游输入、调用 `runAnalysis`、回填输出端口。 |
| `run-session.ts` / `run-session.test.ts` | 分析运行状态、工作流事件处理与日志追加。 |
| `run-summary.ts` | 平台 `RunSummary v3` 的 TypeScript 镜像，含 `artifact_index`、`child_runs`、`extensions`。 |
| `run-summary-view.ts` | GUI 本地结果视图解析，把 `run_summary.json` 转换为页面可直接渲染的 view model。 |
| `artifact.ts` | 产物列表与图件资源类型定义。 |
| `request-preview.ts` | 本地请求 JSON 导入/预览的载荷类型。 |
| `check-report.ts` | `genomelens check -j` 结构化环境报告的前端镜像与展示辅助。 |
| `project.ts` | 项目列表与创建相关的 Tauri 载荷。 |
| `version.ts` | 版本信息载荷。 |
| `jcvi-meow.ts` / `.test.ts` | JCVI meow 品牌体验、能力入口 view model 与工作流预设 helpers。 |
| `validation.ts` | 表单字段级校验草案。 |
| `index.ts` | 模型统一导出入口。 |

## 设计原则

1. **边界显式转换**：平台 JSON 字段保持 `snake_case`，GUI 本地草稿/视图模型可用 `camelCase`，但必须在服务层或边界适配器处显式转换。
2. **GUI 不复制平台逻辑**：GUI 不实现 `WorkflowPlanner`、输入预处理、产物归档或 summary 汇总；只构造请求 JSON 并调用 `analyze run`。
3. **结果消费基于 `artifact_index`**：结果页优先读取 `run_summary.json` 与 `artifact_index`，不解析 stdout。
4. **本地状态持久化**：任务预设与图状态暂存 `localStorage`，后续可替换为服务端项目持久化。

## 旧模型状态

- `AnalysisRequest v1` 及相关草稿已移除，当前源码不再依赖旧协议字段（`task_kind`、`method_config`、`one_stop_workflow_id`、`sub_module_id`、`port_bindings`、`composition`）。
- 若历史迁移语境需要提及旧协议，应明确标注为“历史/已归档”。

## 后续待补齐

- 工作台节点编排：数据节点 → 子模块输入端口的拖拽连线完整闭环。
- 子模块流水线运行验证：串联 `jcvi.pairwise` → `jcvi.graphics_dotplot` / `jcvi.graphics_synteny`。
- `workbench-runner.ts` 与全局运行事件、`RunSummary` 回填的端到端测试。
