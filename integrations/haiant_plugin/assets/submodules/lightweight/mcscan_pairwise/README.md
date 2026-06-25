# gljcvi-mcscan-pairwise — 双物种共线性基础分析子模块插件

## 概述

`gljcvi-mcscan-pairwise` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种共线性基础分析**可编排子模块插件。它适合在两个基因组之间先建立最基础的同源与共线性关系，为后续点图、共线性图、核型图和局部共线性分析提供核心中间结果。

该子模块会完成双物种同源搜索、锚点扫描与共线性区块识别，并输出 blast table、anchors、simple、blocks 等结果。它最适合用于“先算清楚两个基因组之间有哪些稳定共线性片段，再决定后面怎么可视化或做候选位点分析”的场景。
运行完成后，通常会得到后续各类双物种图件都可复用的一组基础共线性中间结果。

本目录是 `gljcvi-mcscan-pairwise` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.mcscan_pairwise
```

## 输入端口

| 端口 | 类型 | 说明 |
|------|------|------|
| `species_pair` | dir | 包含两个物种输入文件的目录；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA` |

插件会自动把 `input_dir` 映射到 `species_pair` 端口。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 双物种输入目录；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA`，插件会自动发现文件对并建立同源搜索输入 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `align_soft` | enum | 否 | `blast` | 同源搜索后端：`blast` / `last` / `diamond_blastp`，会影响速度、灵敏度与锚点数量 |
| `dbtype` | enum | 否 | `nucl` | 同源搜索使用的序列类型：`nucl` / `prot` |
| `cscore` | float | 否 | `0.7` | 同源匹配过滤强度，越高通常越严格 |
| `dist` | int | 否 | `20` | 锚点在基因顺序上允许相隔的最大距离 |
| `iter` | int | 否 | `1` | 共线性区块过滤迭代次数，更多迭代通常更保守 |
| `min_block_size` | int | 否 | `1` | 保留一个共线性区块所需的最小基因数 |
| `threads` | int | 否 | `4` | 运行时线程数 |
| `formats` | enum | 否 | `svg` | 输出格式 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

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
  "threads": 8,
  "formats": "svg"
}
```

```powershell
main.exe params.json
```

等价平台入口：

```powershell
GenomeLens.exe analyze run output\submodule_request.json
```

## 注意事项

1. 输入目录必须恰好包含两个物种的文件对。
2. 该子模块的真实调用凭证是 `output/submodule_request.json`；最终结果主要是 anchors、blocks、simple 等中间产物及其相关图件。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
