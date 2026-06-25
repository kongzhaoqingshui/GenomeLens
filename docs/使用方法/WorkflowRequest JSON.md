# WorkflowRequest JSON

`WorkflowRequest` 是 GenomeLens V3 的**一站式工作流**公开任务请求格式。CLI、插件、GUI 和 Agent 把工作流意图表达为同一个 JSON 对象，再交给平台规划器展开为执行计划：

```powershell
GenomeLens.exe analyze run workflow_request.json
```

需要机器可读运行摘要时加 `-j`：

```powershell
GenomeLens.exe analyze run workflow_request.json -j
```

## 模板与 Schema

```powershell
# 输出 WorkflowRequest 模板（仅 synteny）
GenomeLens.exe analyze template workflow synteny

# 输出 WorkflowRequest JSON Schema
GenomeLens.exe analyze schema --kind workflow

# 同时输出 WorkflowRequest 与 SubmoduleRequest 的联合 schema
GenomeLens.exe analyze schema --kind union
```

当前 schema 承诺：

- `schema_version`: `3`
- `kind`: `"workflow_request"`
- `workflow_id`: 仅 `"synteny"`

V3 不再把 `local_synteny`、`graphics_histogram`、`graphics_heatmap` 作为 workflow_id 暴露；后两者已彻底迁移到子模块，通过 `SubmoduleRequest` 调用。

平台不再接受旧 `AnalysisRequest` 字段，例如 `method`、`method_config`、`task_kind`、`one_stop_workflow_id`、`sub_module_id`、`port_bindings` 和 `composition`。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---:|---|
| `schema_version` | 是 | 固定为 `3` |
| `kind` | 是 | 固定为 `workflow_request` |
| `workflow_id` | 是 | 仅允许 `"synteny"` |
| `species` | 否 | 物种输入数组；至少两个物种 |
| `reference_index` | 否 | 0-based 参考物种下标，默认 `0` |
| `inputs` | 否 | 保留字段，一站式工作流一般留空 |
| `parameters` | 否 | 分组参数对象 |
| `output` | 是 | 输出目录、覆盖策略和图件格式 |
| `runtime` | 否 | 配置路径、工具链路径、线程数、日志等运行时设置 |

## Species 输入

每个物种至少包含 `name` 与 `input_mode`：

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
  "min_block_size": 5,
  "allow_simplified_fallback": false
}
```

- `min_block_size` 已从 `runtime` 下沉到 `parameters.synteny`。

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

### `parameters.histogram` / `parameters.heatmap`

这两个分组在 `WorkflowRequest` schema 中保留，但**不用于** `synteny` 工作流本身。它们继续作为 `jcvi.config.json`（engine profile）的默认参数模板存在。直方图与热图的实际调用请使用 `SubmoduleRequest`。

### `parameters.extras`

`extras` 用于暂存尚未进入强类型分组的透传参数。新能力稳定后应优先补充分组参数，而不是长期堆在 `extras`。

## Runtime 字段

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `project_config` | string | `""` | 平台配置文件路径 |
| `engine_config` | string | `""` | 引擎 profile 路径（`jcvi.config.json`） |
| `jcvi_engine` | string | `""` | 显式指定 `jcvi-genomelens` 引擎 |
| `blastn` | string | `""` | 显式指定 `blastn` |
| `makeblastdb` | string | `""` | 显式指定 `makeblastdb` |
| `lastal` | string | `""` | 显式指定 `lastal` |
| `lastdb` | string | `""` | 显式指定 `lastdb` |
| `threads` | integer \| null | `null` | 并行线程数 |
| `min_block_size` | integer \| null | `null` | 已弃用；请写入 `parameters.synteny.min_block_size` |
| `log_level` | string | `"INFO"` | 日志级别 |
| `verbose` | boolean | `false` | 是否启用详细日志 |
| `console_log` | boolean | `false` | 是否同时输出日志到控制台 |

## Synteny 示例

```json
{
  "schema_version": 3,
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
      "iter": 1,
      "min_block_size": 1
    },
    "plot": {
      "dpi": 300
    }
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "runtime": {
    "threads": 4
  }
}
```

`synteny` 会根据输入自动规划：

- 2 个物种且无目标基因：单个 pairwise synteny step。
- 3 个及以上物种且无目标基因：all-vs-all pairwise steps + global karyotype aggregate step。
- 有目标基因：reference-vs-targets pairwise steps + multi local synteny aggregate step。

## 输出摘要

运行后平台写出：

- `inputs/workflow_request.json`：归一化后的请求快照。
- `inputs/input_manifest.json`：平台执行计划或单步引擎 manifest 的用户可见副本。
- `report/run_summary.json`：`RunSummary` schema v3。

`RunSummary` 的扩展数据进入 `extensions`，复合任务子运行记录进入 `child_runs`，图件与中间产物索引进入 `artifact_index`。
