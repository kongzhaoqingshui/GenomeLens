# gljcvi-dotplot — 双物种点图子模块插件

## 概述

`gljcvi-dotplot` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种点图**可编排子模块插件。它把 `params.json` 直接转换为 `analyze submodule jcvi.graphics_dotplot` 调用，不生成 `genomelens_request.json`。

点图（dotplot）以两个物种的染色体为坐标轴，每个点代表一对同源基因，用于直观查看共线性区块、染色体重排、融合、断裂、全基因组复制等事件。本子模块为下游可视化模块，需提供上游 MCscan pairwise 产出的 `.anchors` 文件。

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
| `species_pair` | dir | 是 | 包含两物种 BED/序列的输入目录（由 `input_dir` 映射） |
| `anchors` | file | 是 | 上游 MCscan pairwise 产出的 `.anchors` 文件 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 输入目录（species_pair 端口） |
| `anchors` | file | 是 | — | `.anchors` 文件路径（anchors 端口） |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `10x10` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

子模块可调参数（`figsize`、`dpi`）通过 `--params` 转发给 `analyze submodule`。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

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

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_dotplot --input-ports "{\"species_pair\": \"input\", \"anchors\": \"pair.anchors\"}" --output-dir output --params "{...}" --formats svg --force
```

## 注意事项

1. `anchors` 为必填上游产物；可由 `gljcvi-mcscan-pairwise` 子模块或 `gljcvi-synteny` 一站式工作流先行生成。
2. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
