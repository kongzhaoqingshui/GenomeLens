# HAIant 参数映射

这份文档回答的核心问题是：HAIant 表单里的每个参数，最终会怎样影响 GenomeLens 的分析请求与结果语义。

HAIant 插件会把 `params.json` 转换为 GenomeLens 平台标准请求 JSON，统一通过 `analyze run` 调用：

- **一站式工作流插件**构造 `WorkflowRequest`，写入 `output/workflow_request.json`，然后调用：

  ```powershell
  <GenomeLens_Path> analyze run output\workflow_request.json
  ```

- **可编排子模块插件**构造 `SubmoduleRequest`，写入 `output/submodule_request.json`，然后调用：

  ```powershell
  <GenomeLens_Path> analyze run output\submodule_request.json
  ```

所有相对路径都按 `params.json` 所在目录解析，因此插件更像一个“参数翻译层”，而不是实际分析实现层。

## 架构说明

当前插件体系采用独立插件模型，产物按两类平台入口和两类子模块组织方式分目录存放：

- `app/onestop/`：一站式工作流插件（生成 `WorkflowRequest`）。
- `app/submodules/lightweight/`：lightweight 子模块插件（生成 `SubmoduleRequest`）。
- `app/submodules/aggregate/`：aggregate 子模块插件（生成 `SubmoduleRequest`）。

平台最新架构只承认两类公开任务协议：`WorkflowRequest`（仅 `synteny`）和 `SubmoduleRequest`（10 个子模块）。  
对用户来说，这意味着 HAIant 中看到的插件虽然很多，但最终都汇聚到统一的平台协议；对维护者来说，这意味着参数映射规则可以稳定收束在这里，而不需要为每个插件重复发明一套私有调用方式。

详见 `ARCHITECTURE.md`。

## 插件与请求类型对照

| 产物路径 | 类型 | 请求文件 | 说明 |
|---|---|---|---|
| `app/onestop/gljcvi-synteny.zip` | 一站式工作流 | `output/workflow_request.json` | 自动流；2 物种 / 多物种 / 目标基因局部共线性 |
| `app/submodules/lightweight/gljcvi-mcscan-pairwise.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种共线性基础结果 |
| `app/submodules/lightweight/gljcvi-catalog-ortholog.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种直系同源目录 |
| `app/submodules/lightweight/gljcvi-dotplot.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种点图（需 `.anchors`） |
| `app/submodules/lightweight/gljcvi-synteny-figure.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种共线性图（需 `.blocks`） |
| `app/submodules/lightweight/gljcvi-karyotype.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种核型图（需 `.blocks`） |
| `app/submodules/lightweight/gljcvi-local-synteny.zip` | 可编排子模块 | `output/submodule_request.json` | 目标基因局部共线性（需 `.blocks` + `target_genes`） |
| `app/submodules/lightweight/gljcvi-histogram.zip` | 可编排子模块 | `output/submodule_request.json` | 数值直方图 |
| `app/submodules/lightweight/gljcvi-heatmap.zip` | 可编排子模块 | `output/submodule_request.json` | 矩阵热图 |
| `app/submodules/aggregate/gljcvi-global-karyotype.zip` | 可编排子模块 | `output/submodule_request.json` | 多物种全局核型总图 |
| `app/submodules/aggregate/gljcvi-multi-local-synteny.zip` | 可编排子模块 | `output/submodule_request.json` | 多物种局部共线性总图 |

## 公共字段

| 平台字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `GenomeLens_Path` | path | 是* | — | 外部 GenomeLens 可执行文件路径（`.exe` / `.cmd` / `.bat`） |
| `input_dir` | dir | 是* | — | 输入目录；在一站式工作流中用于自动发现物种文件对，在双物种基础分析类子模块中映射到 `species_pair` 端口 |
| `output_dir` | dir | 否 | `output` | 结果输出目录；请求文件、运行日志和最终结果都会默认写到这里 |
| `formats` | enum | 否 | `svg` | 输出图片格式：`svg` / `png` / `pdf` / `eps` / `jpg`；不仅影响文件后缀，也影响结果更偏向快速预览还是后续排版 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

## 一站式工作流（`gljcvi-synteny`）字段

`gljcvi-synteny` 主要面向“直接从物种目录起步”的使用方式。下面这些字段会被写入 `WorkflowRequest` 的对应位置：

| 平台字段 | 请求位置 | 默认值 | 说明 |
|---|---|---|---|
| `input_dir` / `species` | `species[]` | — | 自动发现物种文件对或显式物种列表；决定比较对象本身 |
| `input_mode` | 每个物种的 `input_mode` | `bed_cds` | `bed_cds` 或 `gff_genome`；决定平台怎样理解每个物种的原始输入 |
| `reference` | `reference_index` | `0` | 参考物种名称或 1-based 索引；影响多物种比较与局部共线性中的主视角 |
| `threads` | `runtime.threads` | `4` | 运行时工作线程数 |
| `min_block_size` | `parameters.synteny.min_block_size` | `1` | 保留 block 的最小基因数；值越高通常越保守 |
| `align_soft` | `parameters.synteny.align_soft` | `blast` | 同源搜索后端：`blast` / `last` / `diamond_blastp`；影响速度、灵敏度与锚点数量 |
| `dbtype` | `parameters.synteny.dbtype` | `nucl` | 序列类型：`nucl` / `prot`；影响比对策略 |
| `cscore` | `parameters.synteny.cscore` | `0.7` | 同源匹配过滤强度；值越高通常越严格 |
| `dist` | `parameters.synteny.dist` | `20` | 共线性锚点最大基因距离；值越大通常越宽松 |
| `iter` | `parameters.synteny.iter` | `1` | Block 过滤迭代次数；更多迭代通常更保守 |
| `target_gene_ids` | `parameters.local_synteny.target_gene_ids` | — | 目标基因 ID（逗号分隔）；填写后走局部共线性路径 |
| `up` / `down` | `parameters.local_synteny.up` / `down` | `20` | 上下游窗口基因数；共同决定局部图的观察范围 |
| `split_targets` | `parameters.local_synteny.split_targets` | `false` | 多个目标各自出图 |
| `label_targets` | `parameters.local_synteny.label_targets` | `false` | 在图中标注目标基因 |
| `glyphstyle` / `glyphcolor` / `shadestyle` / `figsize` / `dpi` | `parameters.plot.*` | — | 全局图件样式 |
| `optimize_auto` | `parameters.plot.auto_optimization.*` | `false` | 一键开启出图自动优化（figsize / layout / 核型标签） |
| `use_native_local_synteny_renderer` | `parameters.local_synteny.use_native_renderer` | `false` | 启用 GenomeLens 增强局部共线性渲染器，更适合跨染色体或复杂局部区域 |

## 子模块端口与参数

下表列出每个子模块的输入端口（`inputs`）与可调参数（`parameters`）。可以把它理解为：HAIant 表单里哪些字段决定“我要分析什么”，哪些字段决定“我要把结果画成什么样子”。

- lightweight 子模块：输入是原始数据或轻量中间产物。
- aggregate 子模块：输入是 `tracks`、`edges`、聚合 `blocks`、merged BED 等构造式聚合输入，通常由平台聚合步骤或一站式工作流自动准备。

### `gljcvi-mcscan-pairwise`（`jcvi.mcscan_pairwise`）

- 端口：`species_pair`（由 `input_dir` 映射）。
- 参数：`align_soft`、`dbtype`、`cscore`、`dist`、`iter`、`min_block_size`。
- `threads` 写入 `runtime.threads`。

### `gljcvi-catalog-ortholog`（`jcvi.catalog_ortholog`）

- 端口：`species_pair`（由 `input_dir` 映射）。
- 参数：`align_soft`、`dbtype`、`cscore`、`dist`、`iter`、`min_block_size`。
- `threads` 写入 `runtime.threads`。

### `gljcvi-dotplot`（`jcvi.graphics_dotplot`）

- 端口：`species_pair`（`input_dir`）、`anchors`（必填 `.anchors`）。
- 参数：`figsize`、`dpi`。主要影响点图的可读性与输出质量，不改变锚点本身。

### `gljcvi-synteny-figure`（`jcvi.graphics_synteny`）

- 端口：`species_pair`（`input_dir`）、`blocks`（必填 `.blocks`）、`layout`（可选 `.layout`）。
- 参数：`glyphstyle`、`glyphcolor`、`shadestyle`、`figsize`、`dpi`。这些参数主要影响基因块、连线和图面呈现风格。

### `gljcvi-karyotype`（`jcvi.graphics_karyotype`）

- 端口：`species_pair`（`input_dir`）、`blocks`（必填 `.blocks`）。
- 参数：`figsize`、`dpi`。主要影响染色体轨道和连线的展示比例与清晰度。

### `gljcvi-local-synteny`（`jcvi.local_synteny`）

- 端口：`species_pair`（`input_dir`）、`blocks`（必填 `.blocks`）、`target_genes`（由 `target_genes` / `target_gene_ids` 逗号串拆分）。
- 参数：`up`、`down`、`split_targets`、`label_targets`、`use_native_local_synteny_renderer`。其中 `up/down` 决定观察窗口大小，后者几个参数决定局部图的组织和可读性。

### `gljcvi-histogram`（`jcvi.graphics_histogram`）

- 端口：`numeric_files`（由 `input_files` 逗号串或 JSON 数组映射）。
- 参数：`histogram_columns`、`histogram_bins`、`histogram_vmin`、`histogram_vmax`、`histogram_xlabel`、`histogram_title`、`histogram_base`、`histogram_facet`、`histogram_fill`。这些字段主要决定读取哪部分数值以及分布图如何呈现。

### `gljcvi-heatmap`（`jcvi.graphics_heatmap`）

- 端口：`matrix_csv`（由 `input_file` 映射）。
- 参数：`groups`、`rowgroups`、`horizontalbar`、`cmap`、`figsize`、`dpi`。这些字段主要影响矩阵分组信息的展示方式和热图视觉表达。

### `gljcvi-global-karyotype`（`jcvi.graphics_karyotype_global`）

- 端口：`tracks`（物种轨道 `{name, bed}` 列表）、`edges`（共线性边 `{i, j, simple}` 列表）。
- 参数：`figsize`、`dpi`。只影响总图展示比例与清晰度，不改变聚合关系本身。

### `gljcvi-multi-local-synteny`（`jcvi.local_synteny_multi`）

- 端口：`tracks`（`{name, bed}` 列表）、`blocks`（聚合 blocks 路径）、`bed`（聚合 BED 路径）、`target_genes`（目标基因 ID 列表）。
- 参数：`up`、`down`、`split_targets`、`label_targets`、`use_native_local_synteny_renderer`。这些参数主要决定局部多物种总图的窗口大小与出图方式。

## 输出约定

所有插件都保证写入 `run.log`。请求 JSON 也写入 `output_dir`，这样用户不仅能拿到最终结果，也能回看“当时平台实际收到了什么分析请求”：

```text
output/workflow_request.json   # 一站式工作流
output/submodule_request.json  # 可编排子模块
output/run.log
```

一站式工作流插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze run output\workflow_request.json
```

可编排子模块插件实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze run output\submodule_request.json
```

当 `GenomeLens_Path` 不是 `.cmd` / `.bat` 时，直接调用可执行文件。
