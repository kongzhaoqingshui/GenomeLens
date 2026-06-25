# GenomeLens HAIant plugin（智然体插件）

这一集成层把 GenomeLens 的比较基因组学能力接入到 HAIant（智然体）里，让用户在插件表单中直接完成共线性分析、直系同源整理和论文级图件输出，而不需要手写命令。平台能力只有两类，但子模块插件继续细分为 lightweight / aggregate 两种编排语义：

1. **一站式工作流插件**：构造 `WorkflowRequest` JSON 并调用 `analyze run`，由平台自动完成路由与聚合。
2. **可编排子模块插件**：构造 `SubmoduleRequest` JSON 并调用 `analyze run`，输入/输出通过端口显式传递。
   - **lightweight 子模块**：输入是单一任务域内的原始数据或轻量中间产物，不要求调用方先构造跨 pair / 跨物种聚合输入。
   - **aggregate 子模块**：输入是 `tracks`、`edges`、聚合 `blocks`、merged BED 等构造式聚合输入，用于总图或汇总结果。

平台最新架构只承认这两类公开任务协议：`WorkflowRequest`（仅 `synteny`）和 `SubmoduleRequest`（10 个子模块）。所有插件本身都不实现分析算法；真正的同源搜索、共线性识别、聚合绘图与结果归档由外部 GenomeLens 可执行文件完成。

## 当前范围

### 一站式工作流插件

- `gljcvi-synteny` — `WorkflowRequest(workflow_id="synteny")` 一键自动流（auto-routes to pairwise / target-gene local / multi-species global + multi-local aggregate）。

### 可编排子模块插件

#### lightweight

- `gljcvi-mcscan-pairwise` — `jcvi.mcscan_pairwise`
- `gljcvi-catalog-ortholog` — `jcvi.catalog_ortholog`
- `gljcvi-dotplot` — `jcvi.graphics_dotplot`
- `gljcvi-synteny-figure` — `jcvi.graphics_synteny`
- `gljcvi-karyotype` — `jcvi.graphics_karyotype`
- `gljcvi-local-synteny` — `jcvi.local_synteny`
- `gljcvi-histogram` — `jcvi.graphics_histogram`
- `gljcvi-heatmap` — `jcvi.graphics_heatmap`

#### aggregate

- `gljcvi-global-karyotype` — `jcvi.graphics_karyotype_global`
- `gljcvi-multi-local-synteny` — `jcvi.local_synteny_multi`

其中 `dotplot`、`synteny-figure`、`karyotype`、`local-synteny` 为下游可视化 lightweight 子模块，需要用户显式提供上游产物（`.anchors` / `.blocks` / `target_genes`）。`global-karyotype` 与 `multi-local-synteny` 属于 aggregate 子模块，通常由一站式 `synteny` 或平台聚合步骤自动准备输入，不建议普通用户手工拼接。一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。

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
