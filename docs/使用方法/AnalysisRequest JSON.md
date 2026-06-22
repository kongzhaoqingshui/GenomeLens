# AnalysisRequest JSON

`AnalysisRequest` 是 CLI、插件、GUI 和后续 Agent 共用的分析请求格式。外部系统可以把请求写成 JSON 后调用：

```powershell
GenomeLens.exe analyze run request.json
```

需要机器可读运行摘要时加 `-j`：

```powershell
GenomeLens.exe analyze run request.json -j
```

## 模板与 schema

输出 mcscan 示例请求：

```powershell
GenomeLens.exe analyze template mcscan > request.json
```

输出 JSON schema：

```powershell
GenomeLens.exe analyze schema > analysis-request.schema.json
```

当前 schema 只承诺：

- `schema_version`: `1`
- `kind`: `analysis_request`
- `method`: `mcscan`

## 自动目录发现

最小请求：

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "input": {
    "mode": "auto_directory",
    "directory": "input"
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "config": {},
  "options": {
    "preset": "auto",
    "min_block_size": 1
  },
  "method_config": {
    "workflow": "graphics_synteny"
  }
}
```

`auto_directory` 会按输入目录里的同名物种文件对自动补齐 `species[]`，支持：

- `species.bed` + `species.cds`
- `species.bed` + `species.pep` / `species.pep.fa` / `species.faa`
- `species.gff3` + `species.fa`

## 显式 species

外部系统也可以直接给出物种文件：

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "input": {
    "mode": "bed_cds",
    "species": [
      {
        "name": "query",
        "input_mode": "bed_cds",
        "bed": "input/query.bed",
        "cds": "input/query.cds"
      },
      {
        "name": "subject",
        "input_mode": "bed_cds",
        "bed": "input/subject.bed",
        "cds": "input/subject.cds"
      }
    ]
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "config": {},
  "options": {
    "preset": "auto",
    "threads": 4,
    "min_block_size": 1
  },
  "method_config": {
    "workflow": "graphics_synteny",
    "align_soft": "blast",
    "dbtype": "nucl"
  }
}
```

`input.reference_index` 使用 0-based 索引，默认第一个物种为参考物种。指定 `method_config.target_gene_ids` 后，流程会进入目标基因局部共线性分析。

## method_config 扩展字段

### 自动优化

`method_config.auto_optimization` 是 GenomeLens 添加的嵌套开关组，与原生 JCVI 参数区分：

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

`graphics_histogram` 不要求物种目录，使用 `method_specific` 输入模式：

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "input": {
    "mode": "method_specific",
    "directory": "numbers.txt"
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "config": {},
  "options": {
    "preset": "auto"
  },
  "method_config": {
    "workflow": "graphics_histogram",
    "histogram_inputs": ["numbers.txt"],
    "histogram_columns": [0],
    "histogram_bins": 40,
    "histogram_title": "Ks histogram"
  }
}
```
