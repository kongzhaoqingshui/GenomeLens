# gljcvi-local-synteny — 目标基因局部共线性图插件

## 概述

`gljcvi-local-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**目标基因局部共线性图**插件。它把 `params.json` 翻译成 GenomeLens `AnalysisRequest`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `local_synteny` 工作流生成目标基因上下游的局部共线性图。

与全局共线性图不同，局部共线性图聚焦于**一个或多个目标基因所在的局部邻域**：以目标基因为中心，向上下游各取若干基因，展示这些基因在参考物种与比较物种之间的排列顺序、方向、同源性以及结构变异。它特别适合候选基因验证、QTL 区间精细定位、保守调控模块分析等场景。

本目录是 `gljcvi-local-synteny` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 生物学意义

- **候选基因功能验证**：锁定与性状相关的目标基因后，查看其邻域是否在同源物种中保守，可为功能注释提供旁证。
- **调控元件与邻居基因挖掘**：保守的局部基因顺序通常意味着保守的顺式调控关系；邻域内的新增、缺失或重排可能伴随调控网络演化。
- **QTL / GWAS 区间解析**：在目标区间内选择代表性基因，可快速判断该区间在参考物种中的同源区域，辅助图位克隆。
- **结构变异精细刻画**：小尺度的倒位、易位、片段重复、基因丢失在局部图中表现为相邻基因连线的交叉、断裂或密度变化。
- **古多倍体单倍型追踪**：在全基因组复制物种中，目标基因的多个旁系同源拷贝往往对应不同的局部邻域，局部图有助于区分这些拷贝。

## 固定工作流

```text
workflow = local_synteny
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
- **`.cds`**：CDS 序列 FASTA，基因 ID 需与 BED 一致；也支持蛋白序列扩展名。

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
- `target_gene_ids` 中的基因 ID 必须能在参考物种 BED/GFF 中找到。
- 相对路径以 `params.json` 所在目录为基准解析。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `genomelens_exe` | file | 是* | — | 外部 GenomeLens 路径 |
| `input_dir` | dir | 是* | — | 输入目录 |
| `output_dir` | dir | 否 | `output` | 输出目录 |
| `reference` | str/int | 否 | `1` | 参考物种 |
| `threads` | int | 否 | `4` | 线程数 |
| `min_block_size` | int | 否 | `1` | 最小 block 基因数 |
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
| `use_native_local_synteny_renderer` | bool | 否 | `false` | 使用原生 matplotlib 渲染器 |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE`。

## 局部共线性专属参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `target_gene_ids` | str | 是 | — | 目标基因 ID，多个用逗号分隔 |
| `up` | int | 否 | `20` | 上游窗口基因数 |
| `down` | int | 否 | `20` | 下游窗口基因数 |
| `split_targets` | bool | 否 | `false` | 每个目标基因单独出图 |
| `label_targets` | bool | 否 | `false` | 在图中高亮标注目标基因 |

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 输出文件说明

```text
output/
├── genomelens_request.json
├── run.log
└── results/figures/
    ├── local_synteny.<target>.svg    # 局部共线性图主文件
    └── ...
```

- `genomelens_request.json`：可重放的请求 JSON。
- `run.log`：运行日志。
- `results/figures/`：最终局部共线性图。当 `split_targets=true` 时，每个目标基因会生成独立图片；否则多个目标基因绘制在一张图中。

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
  "target_gene_ids": "geneA,geneB",
  "up": 15,
  "down": 15,
  "split_targets": true,
  "label_targets": true,
  "shadestyle": "curve",
  "use_native_local_synteny_renderer": false
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze run output\genomelens_request.json
```

## 何时使用

- 只关心一个或几个目标基因及其邻居的共线性关系。
- 需要验证候选基因在物种间的保守邻域。
- 需要一张聚焦的发表级局部共线性图。

## 注意事项

1. `target_gene_ids` 是必填字段；缺少时会报错。
2. 当目标基因在参考物种中存在多个拷贝或位于重叠区域时，建议开启 `split_targets` 避免图像拥挤。
3. `use_native_local_synteny_renderer` 是 GenomeLens 0.9.20 新增的原生 matplotlib 渲染器，支持跨染色体局部窗口；关闭时沿用 JCVI 默认渲染。
4. `up` / `down` 越大，局部图覆盖范围越大，但也越容易引入无关区块。
