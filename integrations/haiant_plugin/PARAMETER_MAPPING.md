# HAIant 参数映射

HAIant 插件把 `params.json` 转换为 GenomeLens 调用：

- **一站式工作流插件**直接对应 `analyze workflow synteny`：根据参数动态生成 `output/jcvi.config.json`，然后直接调用：

  ```powershell
  <GenomeLens_Path> analyze workflow synteny <input_dir> <output_dir> --jcvi-config output\jcvi.config.json
  ```

- **可编排子模块插件**直接调用平台子模块入口：

  ```powershell
  <GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir <output_dir> [--params <json>] [--formats fmt] --force
  ```

所有相对路径都按 `params.json` 所在目录解析。

## 架构说明

当前插件体系为独立插件模型，产物按两个平台类别与子模块 `module_kind` 分目录存放：

- `app/onestop/`：一站式工作流插件（`analyze workflow synteny`）。
- `app/submodules/lightweight/`：lightweight 子模块插件（`analyze submodule`）。
- `app/submodules/aggregate/`：aggregate 子模块插件（`analyze submodule`）。

平台最新架构只承认这两类能力，不存在独立的“工作流插件”或 `analyze run` 入口。
所有插件都不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。
用户需要在 `params.json` 中提供 `GenomeLens_Path`，或预先设置 `GENOMELENS_EXE` 环境变量。

详见 `ARCHITECTURE.md`。

## 插件与调用方式对照

| 产物路径 | 类型 | 固定 workflow / module_id | 说明 |
|---|---|---|---|
| `app/onestop/gljcvi-synteny.zip` | 一站式工作流 | `analyze workflow synteny` | 自动流；2 物种走 `graphics_synteny`，提供 `target_gene_ids` 时走 `local_synteny`，≥3 物种自动拆 pairwise 并聚合全局核型/多物种局部总图 |
| `app/submodules/lightweight/gljcvi-mcscan-pairwise.zip` | 可编排子模块 | `jcvi.mcscan_pairwise` | 双物种同源搜索与 block 计算 |
| `app/submodules/lightweight/gljcvi-catalog-ortholog.zip` | 可编排子模块 | `jcvi.catalog_ortholog` | 双向 ortholog 目录 |
| `app/submodules/lightweight/gljcvi-dotplot.zip` | 可编排子模块 | `jcvi.graphics_dotplot` | 双物种点图（需 `.anchors`） |
| `app/submodules/lightweight/gljcvi-synteny-figure.zip` | 可编排子模块 | `jcvi.graphics_synteny` | 双物种共线性图（需 `.blocks`） |
| `app/submodules/lightweight/gljcvi-karyotype.zip` | 可编排子模块 | `jcvi.graphics_karyotype` | 双物种核型图（需 `.blocks`） |
| `app/submodules/lightweight/gljcvi-local-synteny.zip` | 可编排子模块 | `jcvi.local_synteny` | 目标基因局部共线性（需 `.blocks` + `target_genes`） |
| `app/submodules/lightweight/gljcvi-histogram.zip` | 可编排子模块 | `jcvi.graphics_histogram` | 数值直方图 |
| `app/submodules/lightweight/gljcvi-heatmap.zip` | 可编排子模块 | `jcvi.graphics_heatmap` | 矩阵热图 |
| `app/submodules/aggregate/gljcvi-global-karyotype.zip` | 可编排子模块 | `jcvi.graphics_karyotype_global` | 多物种全局核型总图 |
| `app/submodules/aggregate/gljcvi-multi-local-synteny.zip` | 可编排子模块 | `jcvi.local_synteny_multi` | 多物种局部共线性总图 |

## 公共字段

| 平台字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `GenomeLens_Path` | path | 是* | — | 外部 GenomeLens 可执行文件路径（`.exe` / `.cmd` / `.bat`） |
| `input_dir` | dir | 是* | — | 输入目录；映射到 `species_pair` 端口或一站式工作流的目录发现 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `formats` | enum | 否 | `svg` | 输出图片格式：`svg` / `png` / `pdf` / `eps` / `jpg`；通过 `--formats` 转发，单选 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

## 一站式工作流（`gljcvi-synteny`）字段

`gljcvi-synteny` 把以下字段写入 `jcvi.config.json`：

| 平台字段 | 配置字段 | 默认值 | 说明 |
|---|---|---|---|
| `input_dir` / `species` | 目录发现 / `species[]` | — | 自动发现物种文件对或显式物种列表 |
| `input_mode` | 每个物种的 `input_mode` | `bed_cds` | `bed_cds` 或 `gff_genome` |
| `reference` | `mcscan.reference` | `1` | 参考物种名称或 1-based 索引 |
| `threads` | `runtime.threads` | `4` | 运行时工作线程数 |
| `min_block_size` | `mcscan.min_block_size` | `5` | 保留 block 的最小基因数 |
| `align_soft` | `mcscan.align_soft` | `blast` | 比对后端：`blast` / `last` / `diamond_blastp` |
| `dbtype` | `mcscan.dbtype` | `nucl` | 序列类型：`nucl` / `prot` |
| `cscore` | `mcscan.cscore` | `0.7` | 同源匹配过滤强度 |
| `dist` | `mcscan.dist` | `20` | 共线性锚点最大基因距离 |
| `iter` | `mcscan.iter` | `1` | Block 过滤迭代次数 |
| `target_gene_ids` | `local_synteny.target_gene_ids` | — | 目标基因 ID（逗号分隔）；填写后自动切换 `local_synteny` |
| `up` / `down` | `local_synteny.up` / `down` | — | 上下游窗口基因数 |
| `split_targets` | `local_synteny.split_targets` | `false` | 多个目标各自出图 |
| `label_targets` | `local_synteny.label_targets` | `false` | 在图中标注目标基因 |
| `optimize_auto` | `local_synteny.auto_optimization.*` | `false` | 一键开启出图自动优化（figsize / layout / 核型标签） |
| `allow_simplified_fallback` | `mcscan.allow_simplified_fallback` | `false` | 诊断开关；正式流程保持关闭 |

## 子模块端口与参数

下表列出每个子模块的输入端口（`--input-ports`）与可调参数（`--params`）。端口字段从 `params.json` 解析为绝对路径或列表，参数字段按声明类型强制转换。

- lightweight 子模块：输入是原始数据或轻量中间产物。
- aggregate 子模块：输入是 `tracks`、`edges`、聚合 `blocks`、merged BED 等构造式聚合输入，通常由平台聚合步骤或一站式工作流自动准备。

### `gljcvi-mcscan-pairwise`（`jcvi.mcscan_pairwise`）

- 端口：`species_pair`（由 `input_dir` 映射）。
- 参数：`align_soft`、`dbtype`、`cscore`、`dist`、`iter`、`min_block_size`、`threads`。

### `gljcvi-catalog-ortholog`（`jcvi.catalog_ortholog`）

- 端口：`species_pair`（由 `input_dir` 映射）。
- 参数：`align_soft`、`dbtype`、`cscore`、`dist`、`iter`、`min_block_size`、`threads`。

### `gljcvi-dotplot`（`jcvi.graphics_dotplot`）

- 端口：`species_pair`（`input_dir`）、`anchors`（必填 `.anchors`）。
- 参数：`figsize`、`dpi`。

### `gljcvi-synteny-figure`（`jcvi.graphics_synteny`）

- 端口：`species_pair`（`input_dir`）、`blocks`（必填 `.blocks`）、`layout`（可选 `.layout`）。
- 参数：`glyphstyle`、`glyphcolor`、`shadestyle`、`figsize`、`dpi`。

### `gljcvi-karyotype`（`jcvi.graphics_karyotype`）

- 端口：`species_pair`（`input_dir`）、`blocks`（必填 `.blocks`）。
- 参数：`figsize`、`dpi`。

### `gljcvi-local-synteny`（`jcvi.local_synteny`）

- 端口：`species_pair`（`input_dir`）、`blocks`（必填 `.blocks`）、`target_genes`（由 `target_genes` / `target_gene_ids` 逗号串拆分）。
- 参数：`up`、`down`、`split_targets`、`label_targets`、`use_native_local_synteny_renderer`。

### `gljcvi-histogram`（`jcvi.graphics_histogram`）

- 端口：`numeric_files`（由 `input_files` 逗号串或 JSON 数组映射）。
- 参数：`histogram_columns`、`histogram_bins`、`histogram_vmin`、`histogram_vmax`、`histogram_xlabel`、`histogram_title`、`histogram_base`、`histogram_facet`、`histogram_fill`。

### `gljcvi-heatmap`（`jcvi.graphics_heatmap`）

- 端口：`matrix_csv`（由 `input_file` 映射）。
- 参数：`groups`、`rowgroups`、`horizontalbar`、`cmap`、`figsize`、`dpi`。

### `gljcvi-global-karyotype`（`jcvi.graphics_karyotype_global`）

- 端口：`tracks`（物种轨道 `{name, bed}` 列表）、`edges`（共线性边 `{i, j, simple}` 列表）。
- 参数：`figsize`、`dpi`。

### `gljcvi-multi-local-synteny`（`jcvi.local_synteny_multi`）

- 端口：`tracks`（`{name, bed}` 列表）、`blocks`（聚合 blocks 路径）、`bed`（聚合 BED 路径）、`target_genes`（目标基因 ID 列表）。
- 参数：`up`、`down`、`split_targets`、`label_targets`、`use_native_local_synteny_renderer`。

## 输出约定

可编排子模块插件只保证写入 `run.log`，请求参数直接随 `analyze submodule` 命令传递：

```text
output/run.log
```

一站式工作流插件 `gljcvi-synteny` 在 `output_dir` 下写入：

```text
output/jcvi.config.json
output/run.log
```

一站式工作流插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze workflow synteny input output --jcvi-config output\jcvi.config.json
```

可编排子模块插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze submodule jcvi.mcscan_pairwise --input-ports "{\"species_pair\": \"input\"}" --output-dir output --params "{...}" --formats svg --force
```

当 `GenomeLens_Path` 不是 `.cmd` / `.bat` 时，直接调用可执行文件。
