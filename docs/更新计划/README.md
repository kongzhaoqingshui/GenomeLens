# GenomeLens 更新计划

> 本文档汇总当前版本状态、近期发布内容与后续功能路线图。

## 当前状态

项目已发布 **v1.0.0-preview-1**，进入 1.0.0 正式发布前的最后验证阶段。`v1.0.0` 将在核心功能全部补齐后正式发布。

## 版本节奏

| 版本 | 主题 | 目标时间 | 关键内容 |
|------|------|----------|----------|
| v1.0.0-preview-1 | 预览版 | 已发布 | Cython 扩展纳入打包、跨轨补充线几何修复、连线宽度对齐 JCVI、PyInstaller 动态导入修复、更新日志重构 |
| v0.9.22 | 重要更新 | 已发布 | 一站式工作流收束为单一 `synteny` 工作流，HAIant 插件同步重命名与扩展 |
| v0.9.20 / v0.9.21 | 重要更新 | 已发布 | 原生局部共线性渲染器、独立 `--use-native-local-synteny-renderer`、先行 GUI `JCVI meow`、Docker 开发环境、文档统一、核心数据模型注释规范 |
| v0.9.7 | 架构整理与功能补齐 | 已发布 | `analysis/requests/` 结构重组、engine workflow `_assert_ok` 去重、清理死代码、JCVI 子任务 CLI、多物种局部共线性总图 |
| v0.9.6 | CLI 进度与出图回退 | 已发布 | 紧凑进度报告、`trim_cross_chromosome_blocks` 与 `rewrite_layout_links` 回退、Pyright 修复 |
| v0.9.5 | 日志与出图尺寸 | 已发布 | 控制台静默模式、JCVI 出图尺寸取整 |
| v0.9.4 | 多物种局部共线性 + 出图自动优化 | 已发布 | 多物种局部共线性图、plot 自动优化 |
| v0.9.3 | JCVI 子任务 CLI | 已发布 | `analyze mcscan jcvi <subtask>` 直接调用 JCVI 子命令 workflow |
| v0.9.2 | 外部配置与插件化 | 已发布 | `analyze run <request.json>`、`analyze template/schema`、智然体插件接入 |
| v0.9.1 | 可观测性 | 已发布 | 结构化 `run.log`、CLI `--verbose` / `--log-level`、失败上下文 |
| v0.9.0 | 体验与输入优化 | 已发布 | CLI 分页帮助、`analyze mcscan jcvi` 子命令、局部共线性目标基因高亮、自动目录输入混用模式、文档刷新 |
| v1.1.0 | GUI | 后续迭代 | Tauri 桌面 GUI 初版 |
| v1.2.0 / mac 分支 | 跨平台 | 后续迭代 | macOS 端与 mac GUI 预览版本 |

## 近期提交概要

自仓库干净起点以来主要变更：

- `fix(cli): page mcscan help` — `analyze mcscan` 帮助分页
- `feat(local_synteny): highlight target genes in local blocks` — 局部共线性图中红色高亮目标基因
- `fix(cli): refine mcscan jcvi help` — 将 `jcvi` 作为 `analyze mcscan` 的必需子命令
- `chore: ignore codex local skills` — 仓库不再跟踪 `.codex/` 本地技能文件
- `docs: refresh primary project documentation` — 刷新 README、CLI、使用方法与开发手册文档
- `docs` — 清理已过时或重复的规划文档
- `feat(input): allow mixed auto directory modes` — 同一目录支持不同物种混用输入模式
- `chore(release): bump version to 0.9.0` — 版本号回退到 0.9.x 预发布阶段

详见 [更新日志](./更新日志.md) 与 [计划更新的内容](./计划更新的内容.md)。
