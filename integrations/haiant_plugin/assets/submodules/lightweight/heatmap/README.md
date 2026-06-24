# gljcvi-heatmap — 矩阵热图子模块插件

## 概述

`gljcvi-heatmap` 是 GenomeLens 在 HAIant（智然体）平台上的**矩阵热图**可编排子模块插件。它把 `params.json` 直接转换为 `analyze submodule jcvi.graphics_heatmap` 调用，不生成 `genomelens_request.json`。

该子模块适用于展示基因表达矩阵、共线性计数矩阵等二维数值数据。

本目录是 `gljcvi-heatmap` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.graphics_heatmap
```

## 输入端口

| 端口 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `matrix_csv` | file | 是 | 输入矩阵 CSV 文件（由 `input_file` 映射） |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_file` | file | 是 | — | 输入矩阵 CSV 文件路径（matrix_csv 端口） |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `cmap` | str | 否 | `""` | matplotlib 颜色映射名称 |
| `groups` | bool | 否 | `false` | 是否按列分组聚类 |
| `rowgroups` | file | 否 | `""` | 行分组文件路径 |
| `horizontalbar` | bool | 否 | `false` | 是否在顶部绘制水平颜色条 |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `8x8` |
| `dpi` | int | 否 | `300` | 分辨率 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

子模块可调参数通过 `--params` 转发给 `analyze submodule`。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_file": "matrix.csv",
  "output_dir": "output",
  "cmap": "viridis",
  "groups": false,
  "formats": "svg"
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_heatmap --input-ports "{\"matrix_csv\": \"matrix.csv\"}" --output-dir output --params "{...}" --formats svg --force
```

## 注意事项

1. 输入矩阵 CSV 的第一行通常作为列标题。
2. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
