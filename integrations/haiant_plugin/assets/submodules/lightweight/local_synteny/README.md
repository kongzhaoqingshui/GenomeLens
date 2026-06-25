# gljcvi-local-synteny — 目标基因局部共线性图子模块插件

## 概述

`gljcvi-local-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**目标基因局部共线性图**可编排子模块插件。它适合围绕候选基因或感兴趣位点观察上下游邻域在另一个物种中是否仍保持相似顺序、方向和对应关系。

局部共线性图会以目标基因为中心，向上下游各取若干基因，展示这些基因在两个物种间的排列顺序、方向、同源性与结构变异。它特别适合候选基因验证、QTL 区间精细定位、保守调控模块分析，以及“这个基因周边结构在别的物种里还在不在”的问题。
运行完成后，通常会得到围绕目标位点展开的双物种局部共线性图，用于直接检查邻域保守关系与局部结构变化。

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
| `species_pair` | dir | 是 | 包含两个物种输入文件的目录（由 `input_dir` 映射）；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA` |
| `blocks` | file | 是 | 上游双物种共线性基础分析产出的 `.blocks` 文件，用于筛出与目标基因相关的局部保守连接 |
| `target_genes` | list | 是 | 目标基因 ID 列表（由 `target_genes` 逗号串拆分） |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 双物种输入目录；每个物种应按同名前缀成对提供 `BED + CDS/PEP` 或 `GFF/GTF + genome FASTA`，用于恢复目标区域的基因顺序、坐标和物种背景 |
| `blocks` | file | 是 | — | `.blocks` 文件路径（blocks 端口），是局部共线性图抽取保守连接的依据 |
| `target_genes` | str | 是 | — | 目标基因 ID（target_genes 端口），多个用逗号分隔 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `up` | int | 否 | `20` | 每个目标基因上游纳入的基因数，数值越大观察范围越宽 |
| `down` | int | 否 | `20` | 每个目标基因下游纳入的基因数，与 `up` 一起决定局部窗口大小 |
| `split_targets` | bool | 否 | `false` | 每个目标基因单独出图 |
| `label_targets` | bool | 否 | `false` | 在图中标注目标基因 |
| `use_native_local_synteny_renderer` | bool | 否 | `false` | 启用 GenomeLens 增强渲染器，更适合跨染色体命中与复杂局部区域 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

插件会把输入端口、局部窗口参数与输出格式统一写入 `output/submodule_request.json`，再通过平台 `analyze run` 执行。`GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。`target_genes` 兼容 `target_gene_ids` 键名。

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

等价平台入口：

```powershell
GenomeLens.exe analyze run output\submodule_request.json
```

## 注意事项

1. `blocks` 与 `target_genes` 均为必填；其中 `blocks` 可由 `gljcvi-pairwise`（双物种共线性基础分析）或 `gljcvi-synteny`（一站式工作流）先行生成。
2. 当目标基因存在多个拷贝或位于重叠区域时，建议开启 `split_targets` 避免图像拥挤。
3. `use_native_local_synteny_renderer` 会启用 GenomeLens 增强局部共线性渲染器，更适合跨染色体命中、截断轨道与复杂局部窗口；关闭时沿用默认渲染路径。
4. 一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。
5. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
