# gljcvi-dotplot — 双物种点图子模块插件

## 概述

`gljcvi-dotplot` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种点图**可编排子模块插件。它适合做双物种共线性结果的第一眼总览，帮助快速判断是否存在大片段保守、倒位、易位、融合、断裂或全基因组复制信号。

点图（dotplot）以两个物种的染色体为坐标轴，每个点代表一对同源基因。本子模块依赖上游双物种共线性基础分析产出的 `.anchors` 文件，因此特别适合在“先建立基础共线性结果，再快速检查结构轮廓和数据质量”的流程里使用。
运行完成后，通常会得到一张可快速判断大片段保守、倒位、易位、断裂和噪声分布的双物种点图。

本目录是 `gljcvi-dotplot` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.graphics_dotplot
```

## 输入端口

| 端口 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `species_pair` | dir | 是 | 包含两个物种输入文件的目录（由 `input_dir` 映射）；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA` |
| `anchors` | file | 是 | 上游双物种共线性基础分析产出的 `.anchors` 文件，决定点图中同源点的位置与分布格局 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 双物种输入目录；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA`，用于建立点图坐标轴和物种背景信息 |
| `anchors` | file | 是 | — | `.anchors` 文件路径（anchors 端口），是点图落点的核心依据 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `10x10` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

插件会把输入端口、绘图参数与输出格式统一写入 `output/submodule_request.json`，再通过平台 `analyze run` 执行。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "anchors": "pair.anchors",
  "output_dir": "output",
  "figsize": "10x10",
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

1. `anchors` 为必填上游产物；可由 `gljcvi-mcscan-pairwise` 子模块或 `gljcvi-synteny` 一站式工作流先行生成。
2. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
