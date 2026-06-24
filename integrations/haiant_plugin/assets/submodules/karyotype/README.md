# gljcvi-karyotype — 双物种核型共线性图子模块插件

## 概述

`gljcvi-karyotype` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种核型共线性图**可编排子模块插件。它把 `params.json` 直接转换为 `analyze submodule jcvi.graphics_karyotype` 调用，不生成 `genomelens_request.json`。

核型图（karyotype figure）以染色体为轨道，把两个物种的整条染色体并排展示，并用连线/阴影带描绘同源区块，强调染色体级别的对应关系，适合展示全染色体尺度的结构保守性与重排事件。本子模块为下游可视化模块，需提供上游 MCscan pairwise 产出的 `.blocks` 文件。

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
| `species_pair` | dir | 是 | 包含两物种 BED/序列的输入目录（由 `input_dir` 映射） |
| `blocks` | file | 是 | 上游 MCscan pairwise 产出的 `.blocks` 文件 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 输入目录（species_pair 端口） |
| `blocks` | file | 是 | — | `.blocks` 文件路径（blocks 端口） |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `8x6` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

子模块可调参数（`figsize`、`dpi`）通过 `--params` 转发给 `analyze submodule`。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

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

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_karyotype --input-ports "{\"species_pair\": \"input\", \"blocks\": \"pair.blocks\"}" --output-dir output --params "{...}" --formats svg --force
```

## 注意事项

1. `blocks` 为必填上游产物；可由 `gljcvi-mcscan-pairwise` 子模块或 `gljcvi-synteny` 一站式工作流先行生成。
2. 当染色体数量较多或名称较长时，可适当增大 `figsize` 避免标签重叠。
3. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
4. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
