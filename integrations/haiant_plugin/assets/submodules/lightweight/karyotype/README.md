# gljcvi-karyotype — 双物种核型共线性图子模块插件

## 概述

`gljcvi-karyotype` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种核型共线性图**可编排子模块插件。它适合把两个物种的染色体尺度共线性关系整理成一张直观的结构图，用于观察整条染色体或大片段之间的保守、断裂、重排与融合情况。

核型图（karyotype figure）以染色体为轨道，把两个物种的整条染色体并排展示，并用连线/阴影带描绘同源区块。本子模块依赖上游双物种共线性基础分析产出的 `.blocks` 文件，因此更偏向“在已经识别出共线性区块之后，做宏观结构解释和展示”的场景。
运行完成后，通常会得到一张适合汇报或论文整理的双物种染色体尺度共线性结构图。

本目录是 `gljcvi-karyotype` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.graphics_karyotype
```

## 输入端口

| 端口 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `species_pair` | dir | 是 | 包含两个物种输入文件的目录（由 `input_dir` 映射）；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA` |
| `blocks` | file | 是 | 上游双物种共线性基础分析产出的 `.blocks` 文件，决定核型图中哪些染色体片段彼此连接 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 双物种输入目录；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA`，用于解析染色体轨道与长度背景 |
| `blocks` | file | 是 | — | `.blocks` 文件路径（blocks 端口），是核型图结构关系的核心输入 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `8x6` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

插件会把输入端口、图件参数与输出格式统一写入 `output/submodule_request.json`，再通过平台 `analyze run` 执行。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "blocks": "pair.blocks",
  "output_dir": "output",
  "figsize": "8x6",
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

1. `blocks` 为必填上游产物；可由 `gljcvi-mcscan-pairwise`（双物种共线性基础分析）或 `gljcvi-synteny`（一站式工作流）先行生成。
2. 当染色体数量较多或名称较长时，可适当增大 `figsize` 避免标签重叠。
3. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
4. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
