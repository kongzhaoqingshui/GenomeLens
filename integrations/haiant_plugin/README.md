# GenomeLens HAIant plugin（智然体插件）

这一 integration layer（集成层）把 HAIant `params.json` 转换为 GenomeLens 平台入口调用。插件分为两类：

1. **一站式工作流插件**：直接调用 `analyze workflow synteny`，由平台自动完成路由与聚合。
2. **可编排子模块插件**：直接调用 `analyze submodule <module_id>`，输入/输出通过端口显式传递。

平台最新架构只承认这两类能力，不存在独立的“工作流插件”或 `analyze run` 入口。所有插件都不实现分析算法，也不直接调用 JCVI；它们依赖外部 GenomeLens 可执行文件。

## 当前范围

### 一站式工作流插件

- `gljcvi-synteny` — `analyze workflow synteny` 一键自动流（auto-routes to `graphics_synteny` / `local_synteny`，≥3 物种自动拆 pairwise 并聚合全局核型总图与多物种局部总图）。

### 可编排子模块插件

- `gljcvi-mcscan-pairwise` — `jcvi.mcscan_pairwise`
- `gljcvi-catalog-ortholog` — `jcvi.catalog_ortholog`
- `gljcvi-dotplot` — `jcvi.graphics_dotplot`
- `gljcvi-synteny-figure` — `jcvi.graphics_synteny`
- `gljcvi-karyotype` — `jcvi.graphics_karyotype`
- `gljcvi-local-synteny` — `jcvi.local_synteny`
- `gljcvi-histogram` — `jcvi.graphics_histogram`
- `gljcvi-heatmap` — `jcvi.graphics_heatmap`
- `gljcvi-global-karyotype` — `jcvi.graphics_karyotype_global`
- `gljcvi-multi-local-synteny` — `jcvi.local_synteny_multi`

其中 `dotplot`、`synteny-figure`、`karyotype`、`local-synteny` 为下游可视化子模块，需要用户显式提供上游产物（`.anchors` / `.blocks` / `target_genes`）。一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。

所有插件均支持：

- 通过 `GenomeLens_Path` 或 `GENOMELENS_EXE` 指定外部 GenomeLens 可执行文件。
- 相对路径按 `params.json` 所在目录解析。
- 不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。

## 入口

```powershell
main.exe params.json
```

### 一站式工作流插件

插件动态生成 `output/jcvi.config.json`，然后直接调用：

```powershell
<GenomeLens_Path> analyze workflow synteny <input_dir> <output_dir> --jcvi-config output/jcvi.config.json
```

### 可编排子模块插件

插件不写旧式 request，而是直接调用：

```powershell
<GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir output [--params <json>] [--formats fmt] --force
```

子模块可调参数通过 `--params` 转发；图形输出格式通过 `--formats` 转发。

`GenomeLens_Path` 从 `params.json` 读取，未设置时回退到 `GENOMELENS_EXE` 环境变量。

## 目录

- `ARCHITECTURE.md`：插件架构总述
- `PARAMETER_MAPPING.md`：字段与 `analyze workflow synteny` / `analyze submodule` 映射
- `assets/onestop/synteny/`：一站式工作流插件资产
- `assets/submodules/<feature>/`：各子模块插件资产（`config.json`、`params.json`、`README.md`）
- `src/features/onestop/`：一站式工作流入口
- `src/features/submodules/`：子模块入口
- `src/genomelens_haiant_plugin/_core.py`：共享命令组装与路径解析

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
- `app/submodules/gljcvi-<feature>.zip`（10 个）

旧产物目录 `app/workflow-plugins/` 与 `app/gljcvi-auto/` 已废弃，应删除。
