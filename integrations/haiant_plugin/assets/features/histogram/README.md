# gljcvi-histogram — 数值分布直方图插件

## 概述

`gljcvi-histogram` 是 GenomeLens 在 HAIant（智然体）平台上的**数值分布直方图**插件。它把 `params.json` 翻译成 GenomeLens `WorkflowRequest v2`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `graphics_histogram` 生成直方图。

该插件适用于展示 Ks 分布、共线性得分等连续数值的分布情况。

本目录是 `gljcvi-histogram` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定工作流

```text
workflow = graphics_histogram
```

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_files` | list/str | 是 | — | 输入数值文件列表；字符串时用逗号分隔 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |
| `histogram_columns` | list/int | 否 | `[0]` | 要绘制的列索引 |
| `histogram_bins` | int | 否 | `20` | 分箱数量 |
| `histogram_xlabel` | str | 否 | `value` | X 轴标签 |
| `histogram_title` | str | 否 | `""` | 图标题 |
| `histogram_fill` | str | 否 | `white` | 填充色 |
| `dpi` | int | 否 | `300` | 分辨率 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_files": "numbers.txt",
  "output_dir": "output",
  "formats": "svg",
  "histogram_bins": 20,
  "histogram_xlabel": "Ks",
  "histogram_title": "Ks distribution"
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

1. `input_files` 可以是单个文件路径字符串，也可以是 JSON 数组。
2. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
