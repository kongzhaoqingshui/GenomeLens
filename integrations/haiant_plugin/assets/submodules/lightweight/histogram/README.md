# gljcvi-histogram — 数值分布直方图子模块插件

## 概述

`gljcvi-histogram` 是 GenomeLens 在 HAIant（智然体）平台上的**数值分布直方图**可编排子模块插件。它适合把 Ks、距离、打分或其他连续统计量整理成分布图，用于快速判断峰值结构、离散程度和可能的数据分层。

该子模块尤其适合放在“分析结果已经出来，现在想快速看某类数值整体长什么样”的环节。
运行完成后，通常会得到一张或多张可直接判断分布形态、峰值位置和离散程度的统计直方图。

本目录是 `gljcvi-histogram` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.graphics_histogram
```

## 输入端口

| 端口 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `numeric_files` | list | 是 | 数值文件列表（由 `input_files` 逗号串或 JSON 数组映射） |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_files` | list/str | 是 | — | 输入数值文件（numeric_files 端口）；可同时比较多个样本、方法或参数条件下的分布 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `histogram_columns` | list/int | 否 | `[0]` | 要绘制的列索引 |
| `histogram_bins` | int | 否 | `20` | 直方图分箱数量；较少更适合总体趋势，较多更利于观察细节峰形 |
| `histogram_vmin` | float | 否 | — | 数值下界 |
| `histogram_vmax` | float | 否 | — | 数值上界 |
| `histogram_xlabel` | str | 否 | `value` | X 轴标签 |
| `histogram_title` | str | 否 | `""` | 图标题 |
| `histogram_fill` | str | 否 | `white` | 填充色 |
| `histogram_base` | int | 否 | — | 对数底（设置后取对数刻度） |
| `histogram_facet` | bool | 否 | `false` | 是否分面绘制 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

插件会把数值输入、绘图参数与输出格式统一写入 `output/submodule_request.json`，再通过平台 `analyze run` 执行。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_files": "numbers.txt",
  "output_dir": "output",
  "histogram_bins": 20,
  "histogram_xlabel": "Ks",
  "histogram_title": "Ks distribution",
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

1. `input_files` 可以是单个文件路径字符串，也可以是逗号分隔串或 JSON 数组。
2. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
