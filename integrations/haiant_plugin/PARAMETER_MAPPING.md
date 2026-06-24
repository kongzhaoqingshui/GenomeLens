# HAIant 参数映射

HAIant 插件把 `params.json` 转换为 GenomeLens 调用：

- **独立工作流插件**生成 `WorkflowRequest v2` JSON，调用外部 GenomeLens 可执行文件：

  ```powershell
  <GenomeLens_Path> analyze run output\genomelens_request.json
  ```

- **原子子模块插件**直接调用平台子模块入口：

  ```powershell
  <GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir <output_dir>
  ```

- **一站式工作流插件**直接对应 `analyze workflow synteny`：根据参数动态生成 `output/jcvi.config.json`，然后直接调用：

  ```powershell
  <GenomeLens_Path> analyze workflow synteny <input_dir> <output_dir> --jcvi-config output\jcvi.config.json
  ```

所有相对路径都按 `params.json` 所在目录解析。

## 架构说明

当前插件体系为**完全独立的轻量插件**，产物按类别分三个目录存放：

- `app/onestop/`：一站式工作流插件。
- `app/workflow-plugins/`：独立工作流插件（`analyze run` + `WorkflowRequest v2`）。
- `app/submodules/`：原子子模块插件（`analyze submodule`）。

所有插件都不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。
用户需要在 `params.json` 中提供 `GenomeLens_Path`，或预先设置 `GENOMELENS_EXE` 环境变量。

详见 `ARCHITECTURE.md`。

## 插件与调用方式对照

| 产物路径 | 类型 | 固定 workflow / module_id | 说明 |
|---|---|---|---|
| `app/onestop/gljcvi-synteny.zip` | 一站式工作流 | `analyze workflow synteny` | 自动流；2 物种走 `graphics_synteny`，提供 `target_gene_ids` 时走 `local_synteny`，≥3 物种自动拆 pairwise 并聚合全局核型/多物种局部总图 |
| `app/workflow-plugins/gljcvi-dotplot.zip` | 独立工作流 | `graphics_dotplot` | 双物种点图 |
| `app/workflow-plugins/gljcvi-synteny-figure.zip` | 独立工作流 | `graphics_synteny` | 双物种共线性图 |
| `app/workflow-plugins/gljcvi-karyotype.zip` | 独立工作流 | `graphics_karyotype` | 双物种核型图 |
| `app/workflow-plugins/gljcvi-catalog-ortholog.zip` | 独立工作流 | `catalog_ortholog` | 双向 ortholog 目录 |
| `app/workflow-plugins/gljcvi-local-synteny.zip` | 独立工作流 | `local_synteny` | 目标基因局部共线性 |
| `app/workflow-plugins/gljcvi-histogram.zip` | 独立工作流 | `graphics_histogram` | 数值直方图 |
| `app/workflow-plugins/gljcvi-heatmap.zip` | 独立工作流 | `graphics_heatmap` | 矩阵热图 |
| `app/submodules/gljcvi-mcscan-pairwise.zip` | 原子子模块 | `jcvi.mcscan_pairwise` | 双物种同源搜索与 block 计算 |
| `app/submodules/gljcvi-global-karyotype.zip` | 原子子模块 | `jcvi.graphics_karyotype_global` | 多物种全局核型总图 |
| `app/submodules/gljcvi-multi-local-synteny.zip` | 原子子模块 | `jcvi.local_synteny_multi` | 多物种局部共线性总图 |

## 公共字段

| 平台字段 | 类型 | 请求字段 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|---|
| `GenomeLens_Path` | path | — | 是* | — | 外部 GenomeLens 可执行文件路径（`.exe` / `.cmd` / `.bat`） |
| `input_dir` | dir | `species[]`（自动发现）/ `inputs.directory` | 是* | — | 自动发现同名物种文件对的输入目录 |
| `species` | array | `species[]` | 是* | — | 显式物种列表（与 `input_dir` 二选一） |
| `input_mode` | enum | 每个物种的 `input_mode` | 否 | `bed_cds` | `bed_cds` 或 `gff_genome` |
| `output_dir` | dir | `output.directory` | 否 | `output` | 结果输出目录 |
| `reference` | str/int | `reference_index` | 否 | `1` | 参考物种名称或 1-based 索引 |
| `threads` | int | `runtime.threads` | 否 | `4` | 运行时工作线程数 |
| `min_block_size` | int | `runtime.min_block_size` | 否 | `5` | 保留 block 的最小基因数 |
| `formats` | enum | `output.formats` | 否 | `svg` | 输出图片格式：`svg` / `png` / `pdf` / `eps` / `jpg`；所有插件统一使用单选，仅输出一个格式 |
| `align_soft` | enum | `parameters.synteny.align_soft` | 否 | `blast` | 比对后端：`blast` / `last` / `diamond_blastp` |
| `dbtype` | enum | `parameters.synteny.dbtype` | 否 | `nucl` | 序列类型：`nucl` / `prot` |
| `cscore` | float | `parameters.synteny.cscore` | 否 | `0.7` | 同源匹配过滤强度 |
| `dist` | int | `parameters.synteny.dist` | 否 | `20` | 共线性锚点最大基因距离 |
| `iter` | int | `parameters.synteny.iter` | 否 | `1` | Block 过滤迭代次数 |
| `glyphstyle` | enum | `parameters.plot.glyphstyle` | 否 | `""` | 基因形状：`box` / `arrow` |
| `glyphcolor` | enum | `parameters.plot.glyphcolor` | 否 | `""` | 基因着色：`orientation` / `orthogroup` |
| `shadestyle` | enum | `parameters.plot.shadestyle` | 否 | `""` | 连线样式：`curve` / `line` |
| `figsize` | str | `parameters.plot.figsize` | 否 | `""` | 画布尺寸，如 `10x5` |
| `dpi` | int | `parameters.plot.dpi` | 否 | `300` | 图片分辨率 |
| `jcvi_engine` | path | `runtime.jcvi_engine` | 否 | `""` | 显式指定 jcvi-genomelens 引擎 |
| `blastn` | path | `runtime.blastn` | 否 | `""` | 显式指定 blastn |
| `makeblastdb` | path | `runtime.makeblastdb` | 否 | `""` | 显式指定 makeblastdb |
| `optimize_figsize` | bool | `parameters.plot.auto_optimization.optimize_figsize` | 否 | `false` | 自动推导图件尺寸（GenomeLens 扩展） |
| `rewrite_layout_links` | bool | `parameters.plot.auto_optimization.rewrite_layout_links` | 否 | `false` | 改写跨轨道 layout 连线（GenomeLens 扩展） |
| `optimize_karyotype_labels` | bool | `parameters.plot.auto_optimization.optimize_karyotype_labels` | 否 | `false` | 优化全局核型标签（GenomeLens 扩展） |
| `optimize_auto` | bool | `parameters.plot.auto_optimization.*` | 否 | `false` | `gljcvi-synteny` 专用：一键开启上述三项出图自动优化 |
| `allow_simplified_fallback` | bool | `parameters.synteny.allow_simplified_fallback` | 否 | `false` | 诊断开关；正式流程保持关闭 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量；`input_dir` 与 `species` 至少提供一个。

## 局部共线性专属字段

仅 `gljcvi-local-synteny` 与 `gljcvi-synteny`（填写 `target_gene_ids` 时）使用以下字段：

| 平台字段 | 请求字段 | 说明 |
|---|---|---|
| `target_gene_ids` | `parameters.local_synteny.target_gene_ids` | 目标基因 ID，多个用逗号分隔 |
| `up` | `parameters.local_synteny.up` | 上游窗口基因数 |
| `down` | `parameters.local_synteny.down` | 下游窗口基因数 |
| `split_targets` | `parameters.local_synteny.split_targets` | 多个目标各自出图；`gljcvi-synteny` 默认单图全出 |
| `label_targets` | `parameters.local_synteny.label_targets` | 在图中标注目标基因 |
| `use_native_local_synteny_renderer` | `parameters.local_synteny.use_native_renderer` | 使用原生局部共线性渲染器 |

## 直方图专属字段

仅 `gljcvi-histogram` 使用：

| 平台字段 | 请求字段 | 说明 |
|---|---|---|
| `input_files` | `parameters.histogram.inputs` | 输入数值文件列表 |
| `histogram_columns` | `parameters.histogram.columns` | 要绘制的列索引 |
| `histogram_bins` | `parameters.histogram.bins` | 分箱数量 |
| `histogram_xlabel` | `parameters.histogram.xlabel` | X 轴标签 |
| `histogram_title` | `parameters.histogram.title` | 图标题 |
| `histogram_fill` | `parameters.histogram.fill` | 填充色 |

## 热图专属字段

仅 `gljcvi-heatmap` 使用：

| 平台字段 | 请求字段 | 说明 |
|---|---|---|
| `input_file` | `parameters.heatmap.matrix` | 输入矩阵 CSV 文件路径 |
| `cmap` | `parameters.heatmap.cmap` | 颜色映射 |
| `groups` | `parameters.heatmap.groups` | 是否按列分组聚类 |
| `rowgroups` | `parameters.heatmap.rowgroups` | 行分组文件路径 |
| `horizontalbar` | `parameters.heatmap.horizontalbar` | 顶部水平颜色条 |

## 原子子模块端口

### `gljcvi-mcscan-pairwise`

| 端口 | 说明 |
|---|---|
| `species_pair` | 包含两个物种文件对的输入目录 |

### `gljcvi-global-karyotype`

| 端口 | 说明 |
|---|---|
| `tracks` | 物种轨道 `{name, bed}` 列表 |
| `edges` | 共线性边 `{i, j, simple}` 列表 |

### `gljcvi-multi-local-synteny`

| 端口 | 说明 |
|---|---|
| `tracks` | 物种轨道 `{name, bed}` 列表 |
| `blocks` | 聚合 blocks 文件路径 |
| `bed` | 聚合 BED 文件路径 |
| `target_genes` | 目标基因 ID 列表 |

## 输出约定

独立工作流插件在 `output_dir` 下写入：

```text
output/genomelens_request.json
output/run.log
```

原子子模块插件只保证写入 `run.log`，请求参数直接随 `analyze submodule` 命令传递。

一站式工作流插件 `gljcvi-synteny` 在 `output_dir` 下写入：

```text
output/jcvi.config.json
output/run.log
```

独立工作流插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze run output\genomelens_request.json
```

一站式工作流插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze workflow synteny input output --jcvi-config output\jcvi.config.json
```

原子子模块插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze submodule jcvi.mcscan_pairwise --input-ports "{\"species_pair\": \"input\"}" --output-dir output --force
```

当 `GenomeLens_Path` 不是 `.cmd` / `.bat` 时，直接调用可执行文件。
