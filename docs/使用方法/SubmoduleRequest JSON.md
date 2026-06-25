# SubmoduleRequest JSON

`SubmoduleRequest` 是 GenomeLens V3 为**可编排子模块**引入的公开任务请求格式。它与一站式 `WorkflowRequest` 并列，CLI、插件、GUI 和 Agent 都把子模块意图表达为同一个 JSON 对象，再交给平台执行：

```powershell
GenomeLens.exe analyze run submodule_request.json
```

需要机器可读运行摘要时加 `-j`：

```powershell
GenomeLens.exe analyze run submodule_request.json -j
```

## 模板与 Schema

```powershell
# 输出指定子模块的 SubmoduleRequest 模板
GenomeLens.exe analyze template submodule jcvi.graphics_histogram

# 输出 SubmoduleRequest JSON Schema
GenomeLens.exe analyze schema --kind submodule

# 同时输出 WorkflowRequest 与 SubmoduleRequest 的联合 schema
GenomeLens.exe analyze schema --kind union
```

当前 schema 承诺：

- `schema_version`: `3`
- `kind`: `"submodule_request"`
- `module_id`: 平台 `SubModuleRegistry` 中已注册的子模块 ID

平台不再接受旧 `AnalysisRequest` 字段，例如 `method`、`method_config`、`task_kind`、`one_stop_workflow_id`、`sub_module_id`、`port_bindings` 和 `composition`。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---:|---|
| `schema_version` | 是 | 固定为 `3` |
| `kind` | 是 | 固定为 `submodule_request` |
| `module_id` | 是 | 子模块 ID，例如 `jcvi.graphics_histogram` |
| `inputs` | 否 | 端口绑定对象，键为子模块声明的 `port_id` |
| `parameters` | 否 | 模块特定参数对象，由子模块自行解释 |
| `output` | 是 | 输出目录、覆盖策略和图件格式 |
| `runtime` | 否 | 配置路径、工具链路径、线程数、日志等运行时设置 |

## 子模块 ID 列表

当前注册 9 个子模块，按 `module_kind` 分为两类：

- `lightweight`：输入是单一任务域内的原始数据或轻量中间产物。
  - `jcvi.pairwise`：双物种同源搜索与 block 计算；`emit_ortholog=true` 时附带双向 ortholog 目录。
  - `jcvi.graphics_dotplot`：共线性点图。
  - `jcvi.graphics_synteny`：共线性对齐图。
  - `jcvi.graphics_karyotype`：核型共线性图。
  - `jcvi.graphics_histogram`：数值直方图。
  - `jcvi.graphics_heatmap`：矩阵热图。
  - `jcvi.local_synteny`：目标基因局部共线性图。
- `aggregate`：输入是跨 pair / 跨物种聚合后的结构化结果。
  - `jcvi.graphics_karyotype_global`：多物种全局核型总图。
  - `jcvi.local_synteny_multi`：多物种局部共线性总图。

完整端口与参数说明见 [`子模块手册.md`](子模块手册.md)。

## 端口绑定

`inputs` 是**直接绑定端口**的字典，不要嵌套在 `inputs.ports` 下。键是子模块声明的 `port_id`，值可以是文件路径、路径列表或 JSON 对象，取决于端口类型：

- `species_pair`：目录路径，或包含 `reference`/`target` 的字典。
- `artifact`：文件路径，例如 `.anchors`、`.blocks`。
- `value`：任意 JSON 值，例如基因 ID 列表、`tracks`/`edges` 列表。

## 参数对象

`parameters` 是自由键值对象，具体键名由子模块解释。常见约定：

- 同源搜索类子模块：`align_soft`、`dbtype`、`cscore`、`dist`、`iter`、`min_block_size`。
- 可视化类子模块：`figsize`、`dpi`、`glyphstyle`、`glyphcolor`、`shadestyle`。
- 直方图：`columns`、`bins`、`vmin`、`vmax`、`xlabel`、`title`、`facet`、`fill`；也兼容带 `histogram_` 前缀的别名。
- 热图：`cmap`、`groups`、`rowgroups`、`horizontalbar`。
- 局部共线性：`up`、`down`、`split_targets`、`label_targets`、`use_native_local_synteny_renderer`。

## Runtime 字段

与 `WorkflowRequest.runtime` 完全一致：

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
| `min_block_size` | integer \| null | `null` | 最小 block 大小（一般由子模块参数覆盖） |
| `log_level` | string | `"INFO"` | 日志级别 |
| `verbose` | boolean | `false` | 是否启用详细日志 |
| `console_log` | boolean | `false` | 是否同时输出日志到控制台 |

## MCscan pairwise 示例

```json
{
  "schema_version": 3,
  "kind": "submodule_request",
  "module_id": "jcvi.pairwise",
  "inputs": {
    "species_pair": "input"
  },
  "parameters": {
    "align_soft": "blast",
    "dbtype": "nucl",
    "cscore": 0.7,
    "dist": 20,
    "iter": 1,
    "min_block_size": 1
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

## 直方图示例

```json
{
  "schema_version": 3,
  "kind": "submodule_request",
  "module_id": "jcvi.graphics_histogram",
  "inputs": {
    "numeric_files": ["numbers.txt"]
  },
  "parameters": {
    "columns": [0],
    "bins": 40,
    "xlabel": "value",
    "title": "Ks histogram"
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "runtime": {}
}
```

## 热图示例

```json
{
  "schema_version": 3,
  "kind": "submodule_request",
  "module_id": "jcvi.graphics_heatmap",
  "inputs": {
    "matrix_csv": "matrix.csv"
  },
  "parameters": {
    "cmap": "viridis",
    "groups": true
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "runtime": {}
}
```

## 输出摘要

运行后平台写出：

- `inputs/submodule_request.json`：归一化后的请求快照。
- `inputs/input_manifest.json`：平台执行计划或单步引擎 manifest 的用户可见副本。
- `report/run_summary.json`：`RunSummary` schema v3。

`RunSummary` 的扩展数据进入 `extensions`，子运行记录进入 `child_runs`，图件与中间产物索引进入 `artifact_index`。
