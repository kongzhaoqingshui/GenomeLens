# gljcvi-synteny — 双物种共线性图插件

## 概述

`gljcvi-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种共线性图**插件。它把用户填写的 HAIant `params.json` 翻译成 GenomeLens `AnalysisRequest`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `graphics_synteny` 生成双物种共线性图。

与点图不同，共线性图（synteny figure）以染色体条带或轨道的形式展示两个物种之间的保守基因区块（syntenic blocks），并通过连线（shade/link）把同源基因对连接起来。它更强调**已识别的共线性区块**及其在染色体上的相对位置，是发表级比较基因组学文章中最常用的图型之一。

## 生物学意义

共线性图是展示物种间保守基因顺序和染色体结构演化的核心可视化工具。

- **保守基因顺序**：共线性区块代表两个物种从共同祖先继承下来的保守基因排列。区块越大、越连续，说明基因组结构越保守。
- **染色体结构变异**：通过观察同源区块在参考物种与目标物种染色体上的排列，可以推断倒位、易位、染色体融合/断裂等事件。
- **重复与缺失**：某些区块的复制、片段缺失或物种特异性插入会在图中表现为连线中断、区块大小变化或孤立区块。
- **下游基因家族研究**：在识别目标基因所在的共线性区块后，可以进一步挖掘旁系同源（paralogs）和直系同源（orthologs），支撑基因功能演化研究。

## 固定工作流

本插件固定使用 GenomeLens 工作流：

```text
workflow = graphics_synteny
```

插件本身不实现 BLAST、MCscan 或绘图算法，仅完成参数翻译与外部调用。

## 输入要求

插件通过 `input_dir` 自动发现同名物种文件对，支持：

- **BED + CDS/PEP**：例如 `speciesA.bed` + `speciesA.cds`。
- **GFF/GTF + 基因组 FASTA**：例如 `speciesA.gff3` + `speciesA.fa`。

输入目录应包含 **两个物种** 的文件。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `genomelens_exe` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是* | — | 输入目录，自动发现物种文件对 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `reference` | str/int | 否 | `1` | 参考物种名称或 1-based 索引 |
| `threads` | int | 否 | `4` | 运行时线程数 |
| `min_block_size` | int | 否 | `1` | 保留共线性 block 的最小基因数 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |
| `align_soft` | enum | 否 | `blast` | 比对后端：`blast` / `last` / `diamond_blastp` |
| `dbtype` | enum | 否 | `nucl` | 序列类型：`nucl` / `prot` |
| `cscore` | float | 否 | `0.7` | 同源匹配过滤强度 |
| `dist` | int | 否 | `20` | 共线性锚点间最大基因距离 |
| `iter` | int | 否 | `1` | Block 过滤迭代次数 |
| `glyphstyle` | enum | 否 | `""` | 基因形状：`box` / `arrow` |
| `glyphcolor` | enum | 否 | `""` | 基因着色：`orientation` / `orthogroup` |
| `shadestyle` | enum | 否 | `""` | 连线样式：`curve` / `line` |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `10x5` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `optimize_figsize` | bool | 否 | `false` | 自动推导 synteny 图件尺寸 |
| `rewrite_layout_links` | bool | 否 | `false` | 改写跨轨道 layout 连线为邻接链 |
| `optimize_karyotype_labels` | bool | 否 | `false` | 优化全局核型标签位置 |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE` 环境变量。

## 输出产物

```text
output/
├── genomelens_request.json
├── run.log
└── results/figures/          # 双物种共线性图
```

## 使用示例

```json
{
  "genomelens_exe": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "reference": "1",
  "threads": 8,
  "min_block_size": 5,
  "formats": "svg",
  "align_soft": "blast",
  "cscore": 0.7,
  "dist": 20,
  "glyphstyle": "arrow",
  "glyphcolor": "orientation",
  "shadestyle": "curve",
  "figsize": "10x5",
  "dpi": 300
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze mcscan jcvi graphics_synteny input output --force
```

## 何时使用

- 需要发表级的双物种共线性可视化。
- 希望突出显示共线性区块而不是所有同源散点。
- 需要结合基因方向、orthogroup 着色或曲线/直线连线风格进行美化。

## 注意事项

1. `glyphstyle`、`glyphcolor`、`shadestyle` 留空时使用 JCVI 默认样式；显式设置可获得更直观的图示。
2. `min_block_size` 越大，图中保留的共线性区块越少但越可靠；过小可能引入噪声。
3. 与点图一样，本插件面向双物种；多物种请使用 `gljcvi-auto`。
