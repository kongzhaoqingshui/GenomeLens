# gljcvi-synteny — 双物种共线性图插件

## 概述

`gljcvi-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种共线性图**插件。它把 `params.json` 翻译成 GenomeLens `AnalysisRequest`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `graphics_synteny` 生成双物种共线性图。

与共线性点图不同，共线性图（synteny figure）以染色体条带或轨道的形式展示两个物种之间的保守基因区块（syntenic blocks），并通过连线把同源基因对连接起来。它更强调已识别的共线性区块及其在染色体上的相对位置，是发表级比较基因组学文章中最常用的图型之一。

本目录是 `gljcvi-synteny` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 生物学意义

- **保守基因顺序**：共线性区块代表两个物种从共同祖先继承下来的保守基因排列。区块越大、越连续，说明基因组结构越保守。
- **染色体结构变异**：通过观察同源区块在参考物种与目标物种染色体上的排列，可以推断倒位、易位、染色体融合/断裂等事件。
- **重复与缺失**：某些区块的复制、片段缺失或物种特异性插入会在图中表现为连线中断、区块大小变化或孤立区块。
- **下游基因家族研究**：在识别目标基因所在的共线性区块后，可以进一步挖掘旁系同源和直系同源，支撑基因功能演化研究。

## 固定工作流

```text
workflow = graphics_synteny
```

## 输入文件说明

### BED + CDS/PEP 模式

```text
input/
├── speciesA.bed
├── speciesA.cds
├── speciesB.bed
└── speciesB.cds
```

- **`.bed`**：基因坐标文件，至少包含 `chr`、`start`、`end`、`gene_id`。
- **`.cds`**：CDS 序列 FASTA，基因 ID 需与 BED 一致；也支持 `.pep`、`.pep.fa`、`.faa`。

### GFF/GTF + 基因组 FASTA 模式

```text
input/
├── speciesA.gff3
├── speciesA.fa
├── speciesB.gff3
└── speciesB.fa
```

- **`.gff3` / `.gtf`**：基因结构注释。
- **`.fa` / `.fasta`**：基因组序列，序列 ID 需与 GFF 中 `seqid` 匹配。

### 输入目录要求

- 同一目录内恰好包含两个物种。
- 相对路径以 `params.json` 所在目录为基准解析。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `genomelens_exe` | file | 是* | — | 外部 GenomeLens 路径 |
| `input_dir` | dir | 是* | — | 输入目录 |
| `output_dir` | dir | 否 | `output` | 输出目录 |
| `reference` | str/int | 否 | `1` | 参考物种 |
| `threads` | int | 否 | `4` | 线程数 |
| `min_block_size` | int | 否 | `1` | 保留共线性 block 的最小基因数 |
| `formats` | enum | 否 | `svg` | 输出格式 |
| `align_soft` | enum | 否 | `blast` | 比对后端 |
| `dbtype` | enum | 否 | `nucl` | 序列类型 |
| `cscore` | float | 否 | `0.7` | 同源过滤强度 |
| `dist` | int | 否 | `20` | 锚点最大基因距离 |
| `iter` | int | 否 | `1` | 过滤迭代次数 |
| `glyphstyle` | enum | 否 | `""` | 基因形状：`box` / `arrow` |
| `glyphcolor` | enum | 否 | `""` | 基因着色：`orientation` / `orthogroup` |
| `shadestyle` | enum | 否 | `""` | 连线样式：`curve` / `line` |
| `figsize` | str | 否 | `""` | 画布尺寸 |
| `dpi` | int | 否 | `300` | 分辨率 |
| `optimize_figsize` | bool | 否 | `false` | 自动推导尺寸 |
| `rewrite_layout_links` | bool | 否 | `false` | 改写 layout 连线 |
| `optimize_karyotype_labels` | bool | 否 | `false` | 优化核型标签 |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE`。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 输出文件说明

```text
output/
├── genomelens_request.json
├── run.log
└── results/figures/
    ├── query.subject.synteny.svg    # 共线性图主文件
    └── ...
```

- `genomelens_request.json`：可重放的请求 JSON。
- `run.log`：运行日志。
- `results/figures/`：最终共线性图文件。

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

1. `glyphstyle`、`glyphcolor`、`shadestyle` 留空时使用 JCVI 默认样式。
2. `min_block_size` 越大，图中保留的共线性区块越少但越可靠。
3. 本插件面向双物种；多物种请使用 `gljcvi-auto`。
