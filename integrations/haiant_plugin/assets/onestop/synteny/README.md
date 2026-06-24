# gljcvi-synteny — MCscan JCVI 一键自动流插件

## 概述

`gljcvi-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的 **MCscan JCVI 一键自动流** 插件。它根据 `params.json` 动态生成 `output/jcvi.config.json`，并直接调用外部 `GenomeLens.exe`：

```text
<GenomeLens_Path> analyze workflow synteny <input_dir> <output_dir> --jcvi-config output/jcvi.config.json
```

与其他单一功能插件不同，`gljcvi-synteny` **不生成 `genomelens_request.json`**，也不走 `analyze run` 流程。它封装了 GenomeLens 原生的 `analyze workflow synteny` 自动目录分析命令，自动完成物种发现、比对、共线性识别、绘图或局部共线性出图。

本目录是 `gljcvi-synteny` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

---

## 生物学意义

比较基因组学的标准分析链路通常包括：序列比对() → 同源过滤 → 共线性区块识别 → 可视化出图。对于常规的物种对或物种集比较，研究者往往不需要反复调整每个子步骤的参数，只需要一条稳定的端到端流程即可获得全局或局部的共线性结果。

`gljcvi-synteny` 的价值在于：

- **降低使用门槛**：无需分别学习多个子命令的调用方式。
- **标准化分析流程**：自动复用 GenomeLens `analyze workflow synteny` 的目录发现、物种解析、比对、过滤、出图逻辑。
- **兼顾全局与局部**：未指定目标基因时输出全局共线性图；指定目标基因后自动切换到局部共线性图。
- **一致的环境复用**：与所有 HAIant 插件共享同一份外部 GenomeLens 安装。

---

## 工作流自动切换逻辑

```text
未填写 target_gene_ids  →  workflow = graphics_synteny（全局共线性图）
填写 target_gene_ids    →  workflow = local_synteny（目标基因局部共线性图）
```

---

## 输入目录使用方法说明

`gljcvi-synteny` 的输入是一个**普通文件夹**，只需把要分析的物种文件按规则放进去即可。系统会自动识别文件、配对物种、选择输入模式。

### 支持的文件组合（可混用）

每个物种需要**一组**文件，以下两种组合任选其一，同一个文件夹里也可以混着放：

| 组合 | 需要的文件 | 说明 |
|---|---|---|
| BED + CDS/PEP | `物种名.bed` + `物种名.cds` | 最常用；CDS 也支持 `.cds.fa`、`.cds.fasta`；蛋白序列支持 `.pep`、`.pep.fa`、`.pep.fasta`、`.faa` |
| GFF/GTF + 基因组 FASTA | `物种名.gff3` + `物种名.fa` | 也支持 `.gff`、`.gtf`、`.fasta`、`.fna` |

### 命名的唯一规则：同一物种文件名前缀相同

系统靠**去掉扩展名后的文件名前缀**来配对。例如：

```text
input/
├── Athaliana.bed
├── Athaliana.cds
├── Brapa.bed
├── Brapa.cds
├── Crubella.gff3
└── Crubella.fa
```

- `Athaliana.bed` 和 `Athaliana.cds` 会被识别为物种 **Athaliana**。
- `Brapa.bed` 和 `Brapa.cds` 会被识别为物种 **Brapa**。
- `Crubella.gff3` 和 `Crubella.fa` 会被识别为物种 **Crubella**。
- 这个例子是 **BED/CDS 和 GFF/FA 混用**，`gljcvi-synteny` 会自动处理。

### 自动处理规则

1. **至少两个物种**：文件夹里必须能成功配出 ≥2 个物种，否则会报错。
2. **自动配对**：只要前缀相同，系统就会自己找对应的 `.bed`/`.cds` 或 `.gff`/`.fa`。
3. **混用优先 BED+CDS**：如果某个物种同时存在 BED+CDS 和 GFF+FA，系统会优先使用 BED+CDS。

### 常见错误

- **文件前缀不同**：`Athaliana.bed` 配 `Ath.cds` → 系统会认为这是两个物种，且配对失败。
- **只有一个物种** → 报 “输入物种不足”。
- **缺少 CDS 或基因组 FASTA** → 该物种无法被识别。

### 完整示例

```text
my_project/
├── params.json
└── input/
    ├── Arabidopsis.bed
    ├── Arabidopsis.cds
    ├── Brassica.gff3
    └── Brassica.fa
```

对应的 `params.json`：

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "reference": "1"
}
```

系统会自动：

1. 识别 `Arabidopsis`（BED+CDS）和 `Brassica`（GFF+FA）。
2. 默认把排序后的第一个物种（`Arabidopsis`）作为参考物种。
3. 开始自动分析。

---

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
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
| `optimize_auto` | bool | 否 | `false` | 一键开启图件尺寸、layout 连线、核型标签三项自动优化 |
| `allow_simplified_fallback` | bool | 否 | `false` | 诊断开关；正式流程保持关闭 |
| `use_native_local_synteny_renderer` | bool | 否 | `false` | 局部共线性模式下使用原生 matplotlib 渲染器 |

---

## 局部共线性专属参数

填写 `target_gene_ids` 时生效：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `target_gene_ids` | str | 否 | `""` | 目标基因 ID，多个用逗号分隔 |
| `up` | int | 否 | `20` | 上游窗口基因数 |
| `down` | int | 否 | `20` | 下游窗口基因数 |
| `split_targets` | bool | 否 | `false` | 每个目标单独出图（`gljcvi-synteny` 默认单图全出） |
| `label_targets` | bool | 否 | `false` | 在图中标注目标基因 |

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

---

## 输出文件说明

```text
output/
├── jcvi.config.json             # 自动生成的 MCscan JCVI 配置
├── run.log                      # 运行日志
├── intermediates.zip            # 中间文件归档（可安全删除）
├── intermediates.zip.deletable  # 可删除标记
└── results/
    └── figures/
        ├── query.subject.synteny.svg    # 全局共线性图（未填 target_gene_ids）
        └── local_synteny.<target>.svg   # 局部共线性图（填写 target_gene_ids）
```

- **`jcvi.config.json`**：由插件根据 `params.json` 动态生成的 MCscan JCVI 配置文件，schema_version = 2。可直接用于 `GenomeLens.exe analyze workflow synteny --jcvi-config` CLI。
- **`run.log`**：插件与外部 GenomeLens 的运行日志。
- **`results/figures/`**：最终图片文件。全局模式下为共线性图；局部模式下为局部共线性图。
- **`intermediates.zip`**：分析完成后，插件把除 `results` 外的中间文件（比对数据库、anchors、blocks、临时图等）打包到此压缩包。
- **`intermediates.zip.deletable`**：标记文件，提示用户可以安全删除 `intermediates.zip` 以释放空间。

---

## 使用示例

### 全局共线性模式

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "reference": "1",
  "threads": 8,
  "min_block_size": 5,
  "formats": "svg",
  "align_soft": "blast",
  "cscore": 0.7,
  "dist": 20,
  "optimize_auto": true
}
```

### 局部共线性模式

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "reference": "1",
  "threads": 8,
  "min_block_size": 5,
  "formats": "svg",
  "align_soft": "blast",
  "cscore": 0.7,
  "target_gene_ids": "geneA",
  "up": 15,
  "down": 15,
  "label_targets": true,
  "use_native_local_synteny_renderer": true
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze workflow synteny input output --jcvi-config output\jcvi.config.json --force
```

---

## 何时使用

- 希望一条命令跑完比对、过滤、共线性识别与出图。
- 不需要分别调用 `gljcvi-dotplot`、`gljcvi-synteny` 等单功能插件。
- 需要在全局共线性与局部共线性之间快速切换。

---

## 注意事项

1. `gljcvi-synteny` 直接调用 CLI，不生成 `genomelens_request.json`，因此不能通过 `analyze run` 重放。
2. `optimize_auto` 会同时开启 `optimize_figsize`、`rewrite_layout_links`、`optimize_karyotype_labels`，适合快速出图；如需精细控制，请改用单功能插件。
3. 在局部共线性模式下，`split_targets` 默认关闭，多个目标会绘制在一张图中；如需单图，可显式开启。
4. `allow_simplified_fallback` 仅用于诊断，正式分析请保持 `false`。
5. 中间文件归档后原始文件会被删除。
