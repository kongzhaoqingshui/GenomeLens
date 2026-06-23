# gljcvi-catalog-ortholog — 双向直系同源目录插件

## 概述

`gljcvi-catalog-ortholog` 是 GenomeLens 在 HAIant（智然体）平台上的**双向直系同源目录**插件。它把 `params.json` 翻译成 GenomeLens `AnalysisRequest`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `catalog_ortholog` 工作流生成两个物种之间的双向直系同源（bidirectional best-hit ortholog）目录。

与其他生成图形的插件不同，本插件的输出是**表格/列表形式的数据**，记录两个物种之间互为最佳匹配的同源基因对。它是进行基因注释迁移、功能比较、选择压力分析和进化树构建的基础。

## 生物学意义

直系同源（ortholog）是指不同物种中由共同祖先的单一基因通过物种分化而保留下来的基因。识别直系同源是功能基因组学和进化生物学的基础步骤。

- **基因功能注释迁移**：在模式物种中已充分研究的基因，可通过直系同源关系把功能假设迁移到非模式物种。
- **选择压力与适应性进化**：比较直系同源基因的序列分歧（dN/dS、Ks 等）可以推断自然选择、功能约束和适应性演化。
- **保守通路重建**：通过直系同源集合可以推断两个物种共同保守的代谢通路、信号通路和发育程序。
- **基因组组装质量评估**：高比例的双向最佳匹配通常表明两个基因组注释质量较好；异常的缺失或大量多对一关系可能提示组装碎片化或注释错误。

## 固定工作流

```text
workflow = catalog_ortholog
```

该工作流调用 JCVI 的 `jcvi.compara.catalog.ortholog --full`，通过双向最佳 BLAST/LAST 匹配识别直系同源对。

## 输入要求

- **BED + CDS/PEP**：`speciesA.bed` + `speciesA.cds`。
- **GFF/GTF + 基因组 FASTA**：`speciesA.gff3` + `speciesA.fa`。

输入目录应包含 **两个物种**。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `genomelens_exe` | file | 是* | — | 外部 GenomeLens 路径 |
| `input_dir` | dir | 是* | — | 输入目录 |
| `output_dir` | dir | 否 | `output` | 输出目录 |
| `reference` | str/int | 否 | `1` | 参考物种 |
| `threads` | int | 否 | `4` | 线程数 |
| `min_block_size` | int | 否 | `1` | 最小 block 基因数 |
| `formats` | enum | 否 | `svg` | 输出图片格式（本插件以表格为主，但保留格式字段） |
| `align_soft` | enum | 否 | `blast` | 比对后端 |
| `dbtype` | enum | 否 | `nucl` | 序列类型 |
| `cscore` | float | 否 | `0.7` | 同源过滤强度 |
| `dist` | int | 否 | `20` | 锚点最大基因距离 |
| `iter` | int | 否 | `1` | 过滤迭代次数 |
| `optimize_figsize` | bool | 否 | `false` | 自动推导图件尺寸 |
| `rewrite_layout_links` | bool | 否 | `false` | 改写 layout 连线 |
| `optimize_karyotype_labels` | bool | 否 | `false` | 优化核型标签 |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE`。

## 输出产物

```text
output/
├── genomelens_request.json
├── run.log
└── results/                  # 双向直系同源目录文件
    └── *.ortholog.*
```

具体文件名取决于 JCVI `catalog_ortholog` 的命名约定，通常包含两个物种名称以及 `.ortholog` 后缀。文件内容为两列基因 ID，表示互为最佳匹配的同源基因对。

## 使用示例

```json
{
  "genomelens_exe": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "reference": "1",
  "threads": 8,
  "min_block_size": 1,
  "formats": "svg",
  "align_soft": "blast",
  "cscore": 0.7,
  "dist": 20,
  "iter": 1
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze mcscan jcvi catalog_ortholog input output --force
```

## 何时使用

- 需要获得两个物种之间的直系同源基因对列表。
- 准备进行 Ks 分布、选择压力、共表达网络或通路比较研究。
- 希望基于模式物种注释推断非模式物种基因功能。

## 注意事项

1. `catalog_ortholog` 不依赖 MCscan 的共线性过滤，它只要求互为最佳匹配；因此结果可能包含不在共线性区块内的散在直系同源。
2. 如果两个物种经历过全基因组复制，单向最佳匹配可能呈现“一对多”关系，研究者需结合共线性信息进一步筛选。
3. `formats` 字段在本插件中主要用于兼容统一配置，实际核心输出为文本目录。
