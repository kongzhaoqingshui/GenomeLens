# GenomeLens HAIant plugin（智然体插件）

这一集成层把 GenomeLens 的比较基因组学能力接入到 HAIant（智然体）里，让用户可以直接在插件表单中完成双物种或多物种共线性分析、直系同源整理，以及论文级图件输出。它的核心价值不是“帮用户转一次命令”，而是把染色体保守关系、结构重排、复制信号和候选基因邻域保守性这些问题整理成可直接操作、可直接解读的插件入口。平台能力只有两类，但子模块插件继续细分为 lightweight / aggregate 两种编排语义：

1. **一站式工作流插件**：构造 `WorkflowRequest` JSON 并调用 `analyze run`，由平台自动完成路由与聚合。
2. **可编排子模块插件**：构造 `SubmoduleRequest` JSON 并调用 `analyze run`，输入/输出通过端口显式传递。
   - **lightweight 子模块**：输入是单一任务域内的原始数据或轻量中间产物，不要求调用方先构造跨 pair / 跨物种聚合输入。
   - **aggregate 子模块**：输入是 `tracks`、`edges`、聚合 `blocks`、merged BED 等构造式聚合输入，用于总图或汇总结果。

平台最新架构只承认这两类公开任务协议：`WorkflowRequest`（仅 `synteny`）和 `SubmoduleRequest`（10 个子模块）。所有插件本身都不实现分析算法；真正的同源搜索、共线性识别、聚合绘图与结果归档由外部 GenomeLens 可执行文件完成。

## 当前范围

### 一站式工作流插件

- `gljcvi-synteny` — 从原始物种目录直接启动的一站式多物种共线性工作流，可自动衔接双物种基础分析、全局总图和目标位点局部图。

### 可编排子模块插件

#### lightweight

- `gljcvi-mcscan-pairwise` — 双物种共线性基础分析，产出 anchors、blocks 等核心中间结果。
- `gljcvi-catalog-ortholog` — 双物种直系同源目录整理。
- `gljcvi-dotplot` — 双物种共线性点图，适合快速总览宏观结构。
- `gljcvi-synteny-figure` — 双物种共线性图，适合展示基因级或片段级对应关系。
- `gljcvi-karyotype` — 双物种核型图，适合染色体尺度结构比较。
- `gljcvi-local-synteny` — 候选基因或目标位点的局部共线性图。
- `gljcvi-histogram` — 各类数值结果的分布直方图。
- `gljcvi-heatmap` — 矩阵型结果的热图展示。

#### aggregate

- `gljcvi-global-karyotype` — 多物种全局核型总图，汇总跨物种染色体对应关系。
- `gljcvi-multi-local-synteny` — 多物种局部共线性总图，汇总同一目标位点在多个基因组中的邻域结构。

其中 `dotplot`、`synteny-figure`、`karyotype`、`local-synteny` 为下游可视化 lightweight 子模块，需要用户显式提供上游产物（`.anchors` / `.blocks` / `target_genes`）。`global-karyotype` 与 `multi-local-synteny` 属于 aggregate 子模块，通常由一站式 `synteny` 或平台聚合步骤自动准备输入，不建议普通用户手工拼接。一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。

## 怎么选插件

- 如果你手里只有多个物种的原始输入目录，希望直接拿到共线性结果与图件：优先用 `gljcvi-synteny`。
- 如果你已经做完双物种基础共线性，想继续看宏观结构：用 `gljcvi-dotplot` 或 `gljcvi-karyotype`。
- 如果你已经有 `.blocks`，想做更适合正文展示的基因级图：用 `gljcvi-synteny-figure`。
- 如果你想围绕候选基因看上下游邻域保守性：用 `gljcvi-local-synteny`。
- 如果你想把双物种同源关系整理成可检索目录：用 `gljcvi-catalog-ortholog`。
- 如果你手里已经是矩阵或数值结果，只想快速转成图：用 `gljcvi-heatmap` 或 `gljcvi-histogram`。
- 如果你已经准备好了多物种聚合后的 `tracks / edges` 或 `tracks / blocks / bed / target_genes`：再考虑 `gljcvi-global-karyotype` 与 `gljcvi-multi-local-synteny`。

所有插件均支持：

- 通过 `GenomeLens_Path` 或 `GENOMELENS_EXE` 指定外部 GenomeLens 可执行文件。
- 相对路径按 `params.json` 所在目录解析。
- 不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。

## 入口

```powershell
main.exe params.json
```

### 一站式工作流插件

插件动态生成 `output/workflow_request.json`，然后调用：

```powershell
<GenomeLens_Path> analyze run output/workflow_request.json
```

### 可编排子模块插件

插件动态生成 `output/submodule_request.json`，然后调用：

```powershell
<GenomeLens_Path> analyze run output/submodule_request.json
```

子模块可调参数写入 `parameters`，端口绑定写入 `inputs`，输出格式写入 `output.formats`。

`GenomeLens_Path` 从 `params.json` 读取，未设置时回退到 `GENOMELENS_EXE` 环境变量。

## 目录

- `ARCHITECTURE.md`：插件架构总述
- `PARAMETER_MAPPING.md`：字段与 `WorkflowRequest` / `SubmoduleRequest` 的映射
- `assets/onestop/synteny/`：一站式工作流插件资产
- `assets/submodules/lightweight/<feature>/`：lightweight 子模块插件资产
- `assets/submodules/aggregate/<feature>/`：aggregate 子模块插件资产
- `src/features/onestop/`：一站式工作流入口
- `src/features/submodules/lightweight/`：lightweight 子模块入口
- `src/features/submodules/aggregate/`：aggregate 子模块入口
- `src/genomelens_haiant_plugin/_core.py`：共享请求组装与路径解析

## 构建

```powershell
# 一站式工作流插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny

# 可编排子模块插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature mcscan_pairwise
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny_figure
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature histogram
scripts/build_gljcvi_feature_plugin.ps1 -Feature heatmap
scripts/build_gljcvi_feature_plugin.ps1 -Feature global_karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature multi_local_synteny
```

产物目录：

- `app/onestop/gljcvi-synteny.zip`
- `app/submodules/lightweight/gljcvi-<feature>.zip`（8 个）
- `app/submodules/aggregate/gljcvi-<feature>.zip`（2 个）

旧产物目录 `app/workflow-plugins/` 与 `app/gljcvi-auto/` 已废弃，应删除。
