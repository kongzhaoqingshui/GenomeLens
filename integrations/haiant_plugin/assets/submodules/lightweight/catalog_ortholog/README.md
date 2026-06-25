# gljcvi-catalog-ortholog — 双向直系同源目录子模块插件

## 概述

`gljcvi-catalog-ortholog` 是 GenomeLens 在 HAIant（智然体）平台上的**双向直系同源目录**可编排子模块插件。它适合把两个物种之间的高可信同源基因关系整理成可检索目录，用于后续功能映射、候选基因跨物种对应、保守基因集整理和进化分析。

子模块会在同源搜索与共线性约束基础上输出双向最佳匹配（bidirectional best-hit）直系同源目录（`.anchors`、`.ortholog` 等）。换句话说，它不是简单“找像不像”，而是尽量在结构背景也一致的前提下整理更可靠的直系同源关系。

本目录是 `gljcvi-catalog-ortholog` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.catalog_ortholog
```

## 输入端口

| 端口 | 类型 | 说明 |
|------|------|------|
| `species_pair` | dir | 包含两个物种文件对的输入目录 |

插件会自动把 `input_dir` 映射到 `species_pair` 端口。输入目录支持 BED+CDS/PEP 或 GFF/GTF+基因组 FASTA 两种模式，文件名前缀相同即视为同一物种，目录内须恰好包含两个物种。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 双物种输入目录，自动识别同名前缀文件对并建立直系同源识别输入 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `align_soft` | enum | 否 | `blast` | 直系同源识别依赖的同源搜索后端，会影响候选匹配灵敏度与数量 |
| `dbtype` | enum | 否 | `nucl` | 用于直系同源识别的序列类型：`nucl` / `prot` |
| `cscore` | float | 否 | `0.7` | 控制进入直系同源目录的匹配严格程度 |
| `dist` | int | 否 | `20` | 在共线性约束下允许的锚点最大间隔 |
| `iter` | int | 否 | `1` | 共线性背景过滤迭代次数 |
| `min_block_size` | int | 否 | `1` | 支撑直系同源判断的最小区块大小 |
| `threads` | int | 否 | `4` | 运行时线程数 |

子模块可调参数通过 `--params` 转发给 `analyze submodule`。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "align_soft": "blast",
  "dbtype": "nucl",
  "cscore": 0.7,
  "dist": 20,
  "iter": 1,
  "min_block_size": 1,
  "threads": 8
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.catalog_ortholog --input-ports "{\"species_pair\": \"input\"}" --output-dir output --params "{...}" --force
```

## 注意事项

1. 输入目录必须恰好包含两个物种的文件对。
2. 该子模块只输出中间产物（anchors / ortholog 目录），不生成 `genomelens_request.json`。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
