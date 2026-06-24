# WorkflowRequest JSON

`WorkflowRequest` 是 GenomeLens 当前公开任务请求格式。CLI、插件、GUI 和后续 Agent 都应把用户意图表达为同一个 JSON 对象，再交给平台规划器展开为执行计划：

```powershell
GenomeLens.exe analyze run request.json
```

需要机器可读运行摘要时加 `-j`：

```powershell
GenomeLens.exe analyze run request.json -j
```

## 模板与 Schema

```powershell
GenomeLens.exe analyze template synteny > request.json
GenomeLens.exe analyze schema > workflow-request.schema.json
```

当前 schema 承诺：

- `schema_version`: `2`
- `kind`: `"workflow_request"`
- `workflow_id`: `"synteny" | "local_synteny" | "graphics_histogram" | "graphics_heatmap"`

平台不再接受旧 `AnalysisRequest` 字段，例如 `method`、`method_config`、`task_kind`、`one_stop_workflow_id`、`sub_module_id`、`port_bindings` 和 `composition`。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---:|---|
| `schema_version` | 是 | 固定为 `2` |
| `kind` | 是 | 固定为 `workflow_request` |
| `workflow_id` | 是 | 用户要运行的工作流或绘图任务 |
| `species` | 否 | 物种输入数组；绘图型任务可为空 |
| `reference_index` | 否 | 0-based 参考物种下标，默认 `0` |
| `inputs` | 否 | 额外输入对象，子模块端口会放在 `inputs.ports` |
| `parameters` | 否 | 分组参数对象 |
| `output` | 是 | 输出目录、覆盖策略和图件格式 |
| `runtime` | 否 | 配置路径、工具链路径、线程数、日志等运行时设置 |

## Species 输入

每个物种至少包含：

```json
{
  "name": "species_a",
  "input_mode": "bed_cds",
  "bed": "input/species_a.bed",
  "cds": "input/species_a.cds"
}
```

支持两类输入：

- `bed_cds`: `bed` + `cds`，也可由 CLI 自动发现 `.pep`、`.pep.fa`、`.faa`。
- `gff_genome`: `gff` + `genome`，平台会预处理为 BED/CDS。

## 参数分组

`parameters` 按用途拆分，不再使用一个大 `method_config`。

### `parameters.synteny`

```json
{
  "align_soft": "blast",
  "dbtype": "nucl",
  "cscore": 0.7,
  "dist": 20,
  "iter": 1,
  "allow_simplified_fallback": false
}
```

### `parameters.local_synteny`

```json
{
  "target_gene_ids": ["AT1G01010"],
  "up": 20,
  "down": 20,
  "split_targets": false,
  "label_targets": false,
  "use_native_renderer": true
}
```

提供 `target_gene_ids` 后，`synteny` 工作流会从普通多物种/双物种共线性切换到 reference-vs-targets 局部共线性分支。

### `parameters.plot`

```json
{
  "figsize": "",
  "dpi": 300,
  "auto_optimization": {
    "optimize_figsize": true,
    "rewrite_layout_links": true,
    "optimize_karyotype_labels": true
  }
}
```

### `parameters.histogram`

```json
{
  "inputs": ["numbers.txt"],
  "columns": [0],
  "bins": 40,
  "xlabel": "value",
  "title": "Ks histogram"
}
```

### `parameters.heatmap`

```json
{
  "matrix": "matrix.csv",
  "cmap": "viridis",
  "groups": true,
  "horizontalbar": false
}
```

### `parameters.extras`

`extras` 用于暂存尚未进入强类型分组的透传参数。新能力稳定后应优先补充分组参数，而不是长期堆在 `extras`。

## Synteny 示例

```json
{
  "schema_version": 2,
  "kind": "workflow_request",
  "workflow_id": "synteny",
  "species": [
    { "name": "query", "input_mode": "bed_cds", "bed": "input/query.bed", "cds": "input/query.cds" },
    { "name": "subject", "input_mode": "bed_cds", "bed": "input/subject.bed", "cds": "input/subject.cds" }
  ],
  "reference_index": 0,
  "inputs": {},
  "parameters": {
    "synteny": {
      "align_soft": "blast",
      "dbtype": "nucl",
      "cscore": 0.7,
      "dist": 20,
      "iter": 1
    },
    "plot": {
      "dpi": 300
    }
  },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "runtime": { "threads": 4, "min_block_size": 1 }
}
```

`synteny` 会根据输入自动规划：

- 2 个物种：单个 pairwise synteny step。
- 3 个及以上物种且无目标基因：all-vs-all pairwise steps + global karyotype aggregate step。
- 有目标基因：reference-vs-targets pairwise steps + multi local synteny aggregate step。

## Histogram 示例

```json
{
  "schema_version": 2,
  "kind": "workflow_request",
  "workflow_id": "graphics_histogram",
  "species": [],
  "reference_index": 0,
  "inputs": { "ports": { "numeric_files": ["numbers.txt"] } },
  "parameters": {
    "histogram": {
      "inputs": ["numbers.txt"],
      "columns": [0],
      "bins": 40,
      "title": "Ks histogram"
    }
  },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "runtime": {}
}
```

## Heatmap 示例

```json
{
  "schema_version": 2,
  "kind": "workflow_request",
  "workflow_id": "graphics_heatmap",
  "species": [],
  "reference_index": 0,
  "inputs": { "ports": { "matrix_csv": "matrix.csv" } },
  "parameters": {
    "heatmap": {
      "matrix": "matrix.csv",
      "cmap": "viridis",
      "groups": true
    }
  },
  "output": { "directory": "output", "force": true, "formats": ["svg"] },
  "runtime": {}
}
```

## 输出摘要

运行后平台写出：

- `inputs/workflow_request.json`：归一化后的请求快照。
- `inputs/input_manifest.json`：平台执行计划或单步引擎 manifest 的用户可见副本。
- `report/run_summary.json`：`RunSummary` schema v3。

`RunSummary` 的扩展数据进入 `extensions`，复合任务子运行记录进入 `child_runs`，图件与中间产物索引进入 `artifact_index`。
