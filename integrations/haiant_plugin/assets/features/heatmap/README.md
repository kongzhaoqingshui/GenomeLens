# gljcvi-heatmap — 矩阵热图插件

## 概述

`gljcvi-heatmap` 是 GenomeLens 在 HAIant（智然体）平台上的**矩阵热图**插件。它把 `params.json` 翻译成 GenomeLens `WorkflowRequest v2`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `graphics_heatmap` 生成热图。

该插件适用于展示基因表达矩阵、共线性计数矩阵等二维数值数据。

本目录是 `gljcvi-heatmap` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定工作流

```text
workflow = graphics_heatmap
```

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_file` | file | 是 | — | 输入矩阵 CSV 文件路径 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |
| `cmap` | str | 否 | `""` | matplotlib 颜色映射名称 |
| `groups` | bool | 否 | `false` | 是否按列分组聚类 |
| `rowgroups` | file | 否 | `""` | 行分组文件路径 |
| `horizontalbar` | bool | 否 | `false` | 是否在顶部绘制水平颜色条 |
| `dpi` | int | 否 | `300` | 分辨率 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_file": "matrix.csv",
  "output_dir": "output",
  "formats": "svg",
  "cmap": "viridis",
  "groups": false
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze run output\genomelens_request.json
```

## 注意事项

1. 输入矩阵 CSV 的第一行通常作为列标题。
2. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
