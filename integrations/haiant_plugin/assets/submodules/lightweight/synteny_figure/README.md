# gljcvi-synteny-figure — 双物种共线性图可编排子模块插件

## 概述

`gljcvi-synteny-figure` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种共线性图**可编排子模块插件。它适合把两个物种之间已经识别出的保守区块整理成更适合正文或补充材料展示的基因级图件。

共线性图（synteny figure）以染色体条带/轨道形式展示两个物种的保守基因区块，并通过连线把同源基因对连接起来，是发表级比较基因组学最常用的图型之一。相比点图，它更强调“具体是哪些基因和片段彼此对应”。
运行完成后，通常会得到一张适合正文、补充材料或汇报展示的双物种基因级共线性图。

本目录是 `gljcvi-synteny-figure` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.graphics_synteny
```

## 输入端口

| 端口 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `species_pair` | dir | 是 | 包含两个物种输入文件的目录（由 `input_dir` 映射）；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA` |
| `blocks` | file | 是 | 上游双物种共线性基础分析产出的 `.blocks` 文件，决定图中哪些区段与基因建立对应关系 |
| `layout` | file | 否 | 可选的 `.layout` 文件 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 双物种输入目录；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA`，用于构建基因轨道、顺序和物种背景 |
| `blocks` | file | 是 | — | `.blocks` 文件路径（blocks 端口），是共线性图组织连线的核心输入 |
| `layout` | file | 否 | `""` | `.layout` 文件路径（layout 端口） |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `glyphstyle` | enum | 否 | `""` | 基因形状：`box` / `arrow` |
| `glyphcolor` | enum | 否 | `""` | 基因着色：`orientation` / `orthogroup` |
| `shadestyle` | enum | 否 | `""` | 连线样式：`curve` / `line` |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `10x5` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

插件会把输入端口、图件样式参数与输出格式统一写入 `output/submodule_request.json`，再通过平台 `analyze run` 执行。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "blocks": "pair.blocks",
  "layout": "",
  "output_dir": "output",
  "glyphstyle": "arrow",
  "glyphcolor": "orientation",
  "shadestyle": "curve",
  "figsize": "10x5",
  "dpi": 300,
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

1. `blocks` 为必填上游产物；可由 `gljcvi-pairwise`（双物种共线性基础分析）或 `gljcvi-synteny`（一站式工作流）先行生成。
2. `glyphstyle`、`glyphcolor`、`shadestyle` 留空时使用 JCVI 默认样式。
3. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
4. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
