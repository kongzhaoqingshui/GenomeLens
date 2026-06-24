# GenomeLens HAIant plugin（智然体插件）

这一 integration layer（集成层）把 HAIant `params.json` 转换为 GenomeLens 平台入口调用。插件分为三类：

1. **一站式工作流插件**：直接调用 `analyze workflow synteny`，由平台自动完成路由与聚合。
2. **独立工作流插件**：生成 `WorkflowRequest v2` 后调用 `analyze run`，每个插件对应一个单一 JCVI workflow。
3. **原子子模块插件**：直接调用 `analyze submodule`，输入/输出通过端口显式传递。

所有插件都不实现分析算法，也不直接调用 JCVI；它们依赖外部 GenomeLens 可执行文件。

## 当前范围

### 一站式工作流插件

- `gljcvi-synteny` — `analyze workflow synteny` 一键自动流（auto-routes to `graphics_synteny` / `local_synteny`）

### 独立工作流插件

- `gljcvi-dotplot` — `graphics_dotplot`
- `gljcvi-karyotype` — `graphics_karyotype`
- `gljcvi-catalog-ortholog` — `catalog_ortholog`
- `gljcvi-local-synteny` — `local_synteny`
- `gljcvi-synteny-figure` — `graphics_synteny`
- `gljcvi-histogram` — `graphics_histogram`
- `gljcvi-heatmap` — `graphics_heatmap`

### 原子子模块插件

- `gljcvi-mcscan-pairwise` — `jcvi.mcscan_pairwise`
- `gljcvi-global-karyotype` — `jcvi.graphics_karyotype_global`
- `gljcvi-multi-local-synteny` — `jcvi.local_synteny_multi`

所有插件均支持：

- BED+CDS 或 GFF+基因组 FASTA 输入（工作流插件）。
- `input_dir` 自动发现物种文件对，或显式提供 `species[]` 列表（工作流插件）。
- 不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。

## 入口

```powershell
main.exe params.json
```

### 独立工作流插件

插件会先写出稳定的 `genomelens_request.json`，再调用外部 GenomeLens：

```powershell
<GenomeLens_Path> analyze run output/genomelens_request.json
```

### 一站式工作流插件

插件动态生成 `output/jcvi.config.json`，然后直接调用：

```powershell
<GenomeLens_Path> analyze workflow synteny <input_dir> <output_dir> --jcvi-config output/jcvi.config.json
```

### 原子子模块插件

插件不写旧式 request，而是直接调用：

```powershell
<GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir output
```

`GenomeLens_Path` 从 `params.json` 读取，未设置时回退到 `GENOMELENS_EXE` 环境变量。

## 目录

- `ARCHITECTURE.md`：插件架构总述
- `PARAMETER_MAPPING.md`：字段与 `WorkflowRequest v2` / `analyze submodule` 映射
- `assets/features/<feature>/`：各插件的 `config.json`、`params.json`、`README.md`
- `src/features/`：各插件入口
- `src/genomelens_haiant_plugin/_core.py`：共享请求组装与路径解析

## 构建

```powershell
# 一站式工作流插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny

# 独立工作流插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny_figure
scripts/build_gljcvi_feature_plugin.ps1 -Feature histogram
scripts/build_gljcvi_feature_plugin.ps1 -Feature heatmap

# 原子子模块插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature mcscan_pairwise
scripts/build_gljcvi_feature_plugin.ps1 -Feature global_karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature multi_local_synteny
```

产物目录：

- `app/onestop/gljcvi-synteny.zip`
- `app/workflow-plugins/gljcvi-<feature>.zip`
- `app/submodules/gljcvi-<feature>.zip`
