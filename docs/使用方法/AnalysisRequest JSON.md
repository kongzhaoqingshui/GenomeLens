# AnalysisRequest JSON

`AnalysisRequest` 是 CLI、插件、GUI 和后续 Agent 共用的分析请求格式。外部系统把请求写成 JSON 后调用：

```powershell
GenomeLens.exe analyze run request.json
```

需要机器可读运行摘要时加 `-j`：

```powershell
GenomeLens.exe analyze run request.json -j
```

## 模板与 schema

```powershell
GenomeLens.exe analyze template mcscan > request.json
GenomeLens.exe analyze schema > analysis-request.schema.json
```

当前 schema 承诺：

- `schema_version`: `1`
- `kind`: `analysis_request`
- `method`: `mcscan`
- `task_kind`: `"analysis" | "one_stop" | "sub_module" | "composition"`

## task_kind 总览

| `task_kind` | 用途 | 关键字段 |
|---|---|---|
| `analysis` | 旧模式 / 默认 | `input`, `output`, `options`, `method_config` |
| `one_stop` | 一站式工作流 | `one_stop_workflow_id` |
| `sub_module` | 单个子模块 | `sub_module_id`, `port_bindings` |
| `composition` | 可视化组合（未来实现） | `composition` |

## analysis：旧模式（兼容）

### 自动目录发现

最小请求：

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "analysis",
  "input": { "mode": "auto_directory", "directory": "input" },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "config": {},
  "options": { "preset": "auto", "min_block_size": 1 },
  "method_config": { "workflow": "graphics_synteny" }
}
```

`auto_directory` 会按输入目录里的同名物种文件对自动补齐 `species[]`，支持：

- `species.bed` + `species.cds`
- `species.bed` + `species.pep` / `species.pep.fa` / `species.faa`
- `species.gff3` + `species.fa`

### 显式 species

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "analysis",
  "input": {
    "mode": "bed_cds",
    "species": [
      { "name": "query", "input_mode": "bed_cds", "bed": "input/query.bed", "cds": "input/query.cds" },
      { "name": "subject", "input_mode": "bed_cds", "bed": "input/subject.bed", "cds": "input/subject.cds" }
    ]
  },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "config": {},
  "options": { "preset": "auto", "threads": 4, "min_block_size": 1 },
  "method_config": {
    "workflow": "graphics_synteny",
    "align_soft": "blast",
    "dbtype": "nucl"
  }
}
```

`input.reference_index` 使用 0-based 索引，默认第一个物种为参考物种。指定 `method_config.target_gene_ids` 后进入目标基因局部共线性分析。

## one_stop：一站式工作流

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "one_stop",
  "one_stop_workflow_id": "pairwise_synteny",
  "input": { "mode": "auto_directory", "directory": "input" },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "config": {},
  "options": { "preset": "auto", "threads": 4, "min_block_size": 1 },
  "method_config": { "align_soft": "blast", "cscore": 0.7 }
}
```

可用的 `one_stop_workflow_id`：

- `pairwise_synteny`
- `multi_species_synteny`
- `reference_vs_targets`
- `histogram_plot`
- `heatmap_plot`

## sub_module：可编排子模块

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "sub_module",
  "sub_module_id": "jcvi.graphics_histogram",
  "port_bindings": {
    "numeric_files": ["numbers.txt"]
  },
  "input": { "mode": "method_specific" },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "config": {},
  "options": { "preset": "auto" },
  "method_config": {
    "histogram_columns": [0],
    "histogram_bins": 40,
    "histogram_title": "Ks histogram"
  }
}
```

子模块端口表见 [`子模块手册.md`](子模块手册.md)。

## method_config 扩展字段

### 自动优化

`method_config.auto_optimization` 是 GenomeLens 自研优化开关：

```json
{
  "method_config": {
    "workflow": "graphics_synteny",
    "auto_optimization": {
      "optimize_figsize": true,
      "rewrite_layout_links": true,
      "optimize_karyotype_labels": true
    }
  }
}
```

- `optimize_figsize`：自动推导合适画布尺寸。
- `rewrite_layout_links`：全局核型/多物种局部图按链式关系重写 edges。
- `optimize_karyotype_labels`：镜像分布全局核型标签，避免重叠。

### Histogram 纯绘图请求

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "sub_module",
  "sub_module_id": "jcvi.graphics_histogram",
  "port_bindings": { "numeric_files": ["numbers.txt"] },
  "input": { "mode": "method_specific" },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "config": {},
  "options": { "preset": "auto" },
  "method_config": {
    "histogram_columns": [0],
    "histogram_bins": 40,
    "histogram_title": "Ks histogram"
  }
}
```

### Heatmap 请求

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "sub_module",
  "sub_module_id": "jcvi.graphics_heatmap",
  "port_bindings": { "matrix_csv": "matrix.csv" },
  "input": { "mode": "method_specific" },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "config": {},
  "options": { "preset": "auto" },
  "method_config": {
    "cmap": "viridis",
    "groups": true,
    "horizontalbar": false
  }
}
```

## composition：可视化组合（预留）

`task_kind=composition` 用于 GUI 拖拽式编排，按端口连接执行多个子模块。当前 schema 已预留 `composition` 字段，执行层尚未实现。

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "task_kind": "composition",
  "composition": {
    "nodes": [
      { "node_id": "mcscan", "sub_module_id": "jcvi.mcscan_pairwise" },
      { "node_id": "dotplot", "sub_module_id": "jcvi.graphics_dotplot" }
    ],
    "edges": [
      { "from": "mcscan", "output_port": "anchors", "to": "dotplot", "input_port": "anchors" }
    ]
  },
  "input": { "mode": "auto_directory", "directory": "input" },
  "output": { "directory": "output", "force": true, "formats": ["svg"] }
}
```

## 注意

- `task_kind` 省略时默认 `analysis`，保持与旧 `request.json` 兼容。
- `one_stop_workflow_id` 与 `sub_module_id` 互斥；与 `method_config.workflow` 同时存在时以 `task_kind` 选择的路径为准。
