# gljcvi-local-synteny — 目标基因局部共线性图子模块插件

## 概述

`gljcvi-local-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**目标基因局部共线性图**可编排子模块插件。它把 `params.json` 直接转换为 `analyze submodule jcvi.local_synteny` 调用，不生成 `genomelens_request.json`。

局部共线性图聚焦于一个或多个目标基因所在的局部邻域：以目标基因为中心，向上下游各取若干基因，展示这些基因在两个物种间的排列顺序、方向、同源性与结构变异。适合候选基因验证、QTL 区间精细定位、保守调控模块分析。本子模块为下游可视化模块，需提供上游 MCscan pairwise 产出的 `.blocks` 文件与目标基因 ID。

本目录是 `gljcvi-local-synteny` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.local_synteny
```

## 输入端口

| 端口 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `species_pair` | dir | 是 | 包含两物种 BED/序列的输入目录（由 `input_dir` 映射） |
| `blocks` | file | 是 | 上游 MCscan pairwise 产出的 `.blocks` 文件 |
| `target_genes` | list | 是 | 目标基因 ID 列表（由 `target_genes` 逗号串拆分） |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 输入目录（species_pair 端口） |
| `blocks` | file | 是 | — | `.blocks` 文件路径（blocks 端口） |
| `target_genes` | str | 是 | — | 目标基因 ID（target_genes 端口），多个用逗号分隔 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `up` | int | 否 | `20` | 上游窗口基因数 |
| `down` | int | 否 | `20` | 下游窗口基因数 |
| `split_targets` | bool | 否 | `false` | 每个目标基因单独出图 |
| `label_targets` | bool | 否 | `false` | 在图中标注目标基因 |
| `use_native_local_synteny_renderer` | bool | 否 | `false` | 使用 GenomeLens 原生渲染器（支持跨染色体） |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

子模块可调参数通过 `--params` 转发给 `analyze submodule`。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。`target_genes` 兼容 `target_gene_ids` 键名。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "blocks": "pair.blocks",
  "target_genes": "geneA,geneB",
  "output_dir": "output",
  "up": 15,
  "down": 15,
  "split_targets": true,
  "label_targets": true,
  "use_native_local_synteny_renderer": false,
  "formats": "svg"
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.local_synteny --input-ports "{\"species_pair\": \"input\", \"blocks\": \"pair.blocks\", \"target_genes\": [\"geneA\", \"geneB\"]}" --output-dir output --params "{...}" --formats svg --force
```

## 注意事项

1. `blocks` 与 `target_genes` 均为必填；可由 `gljcvi-mcscan-pairwise` 子模块或 `gljcvi-synteny` 一站式工作流先行生成 blocks。
2. 当目标基因存在多个拷贝或位于重叠区域时，建议开启 `split_targets` 避免图像拥挤。
3. `use_native_local_synteny_renderer` 使用 GenomeLens 原生 matplotlib 渲染器，支持跨染色体局部窗口；关闭时沿用 JCVI 默认渲染。
4. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
5. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
