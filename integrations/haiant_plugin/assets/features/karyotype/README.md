# gljcvi-karyotype — 双物种核型共线性图插件

## 概述

`gljcvi-karyotype` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种核型共线性图**插件。它把 `params.json` 翻译成 GenomeLens `AnalysisRequest`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `graphics_karyotype` 生成核型共线性图。

核型图（karyotype figure）以染色体为轨道，把两个物种的整条染色体并排展示，并用连线或阴影带描绘它们之间的同源区块。与共线性图相比，核型图更强调**染色体级别的对应关系**，适合展示全染色体尺度的结构保守性与重排事件。

本目录是 `gljcvi-karyotype` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 生物学意义

- **染色体尺度同源**：以整条染色体为单位展示物种间的同源关系，便于判断染色体融合、断裂、整体复制等大规模事件。
- **核型演化推断**：通过参考物种染色体与目标物种染色体之间的连线模式，可以推断祖先核型、染色体融合/断裂历史。
- **古多倍体痕迹**：在经历过全基因组复制的物种中，会出现“一条参考染色体对应多条目标染色体”或“多条参考染色体与一条目标染色体大片段同源”的模式。
- **细胞遗传学验证**：可与实验核型、FISH 结果相互印证，为基因组组装质量提供独立证据。

## 固定工作流

```text
workflow = graphics_karyotype
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
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `8x6` |
| `dpi` | int | 否 | `300` | 分辨率 |
| `optimize_figsize` | bool | 否 | `false` | 自动推导尺寸 |
| `rewrite_layout_links` | bool | 否 | `false` | 改写 layout 连线 |
| `optimize_karyotype_labels` | bool | 否 | `false` | 优化核型标签位置 |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE`。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 输出文件说明

```text
output/
├── genomelens_request.json
├── run.log
└── results/figures/
    ├── query.subject.karyotype.svg    # 核型共线性图主文件
    └── ...
```

- `genomelens_request.json`：可重放的请求 JSON。
- `run.log`：运行日志。
- `results/figures/`：最终核型图文件。

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
  "figsize": "8x6",
  "dpi": 300,
  "optimize_karyotype_labels": true
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze mcscan jcvi graphics_karyotype input output --force
```

## 何时使用

- 关注染色体级别而不是单个基因区块的演化关系。
- 需要一张图展示两个物种整条染色体之间的同源对应。
- 研究核型演化、染色体融合/断裂、古多倍体残留。

## 注意事项

1. 当物种染色体数量较多或染色体名较长时，建议开启 `optimize_karyotype_labels` 以避免标签重叠。
2. `figsize` 对核型图影响较大，长染色体或较多染色体时可适当增大画布。
3. 核型图同样面向双物种；多物种全局核型请使用 `gljcvi-auto`。
