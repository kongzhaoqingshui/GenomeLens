# gljcvi-dotplot — 双物种点图插件

## 概述

`gljcvi-dotplot` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种点图**插件。它把 `params.json` 翻译成 GenomeLens `WorkflowRequest v2`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终基于 JCVI `graphics_dotplot` 生成双物种同源点图。

点图（dotplot）以两个物种的染色体为坐标轴，每个点代表一对同源基因。通过点的分布，研究者可以直观地看到大规模共线性区块、染色体重排、融合、断裂、重复事件以及物种间的线性对应关系。

本目录是 `gljcvi-dotplot` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 生物学意义

- **共线性区块识别**：沿对角线成簇分布的点即为共线性区块（syntenic blocks），代表两个物种在进化过程中保留的保守基因顺序。
- **染色体演化事件**：偏离对角线的点簇提示染色体倒位（inversion）、易位（translocation）、融合（fusion）或断裂（fission）。
- **全基因组复制（WGD）检测**：在同源多倍体或古多倍体物种中，点图会出现多条平行对角线或网格状模式，是推断多倍化历史的重要依据。
- **近缘物种快速比较**：无需复杂参数，即可获得两个物种整体同源关系的全局视图。

## 固定工作流

```text
workflow = graphics_dotplot
```

## 输入文件说明

插件通过 `input_dir` 自动发现同名物种文件对，支持以下两种输入模式：

### BED + CDS/PEP 模式

每个物种需要两个文件，且文件名前缀（物种名）必须一致：

```text
input/
├── speciesA.bed
├── speciesA.cds
├── speciesB.bed
└── speciesB.cds
```

- **`.bed`**：基因坐标文件，至少包含 `chr`、`start`、`end`、`gene_id` 四列；JCVI 使用基因 ID 作为锚点。
- **`.cds`**：对应基因的 CDS 序列 FASTA，基因 ID 需与 BED 中一致；也支持 `.pep`、`.pep.fa`、`.faa` 蛋白序列。

### GFF/GTF + 基因组 FASTA 模式

```text
input/
├── speciesA.gff3
├── speciesA.fa
├── speciesB.gff3
└── speciesB.fa
```

- **`.gff3` / `.gtf`**：基因结构注释文件，需包含基因位置信息。
- **`.fa` / `.fasta`**：对应基因组序列文件，序列 ID 需与 GFF 中 `seqid` 匹配。

### 输入目录要求

- 同一目录内恰好包含 **两个物种**。
- 若两个物种都提供 BED+CDS，则优先按 `bed_cds` 模式处理；否则按实际扩展名自动识别。
- 所有相对路径以 `params.json` 所在目录为基准解析。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
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
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `10x10` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `optimize_figsize` | bool | 否 | `false` | 自动推导图件尺寸（GenomeLens 扩展） |
| `rewrite_layout_links` | bool | 否 | `false` | 改写跨轨道 layout 连线（GenomeLens 扩展） |
| `optimize_karyotype_labels` | bool | 否 | `false` | 优化全局核型标签（GenomeLens 扩展） |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量；`input_dir` 与 `species` 至少提供一个。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 输出文件说明

插件在 `output_dir` 下生成：

```text
output/
├── genomelens_request.json   # 生成的 WorkflowRequest v2
├── run.log                   # 运行日志
└── results/
    └── figures/
        ├── query.subject.dotplot.svg    # 点图主文件
        └── ...                          # 其他格式（由 formats 决定）
```

- **`genomelens_request.json`**：稳定的请求 JSON，可直接用 `GenomeLens.exe analyze run` 重放。
- **`run.log`**：插件与外部 GenomeLens 的运行日志，便于排查比对、过滤、绘图阶段的异常。
- **`results/figures/`**：最终点图文件。命名通常形如 `<query>.<subject>.dotplot.<formats>`，具体取决于 JCVI 引擎对 `graphics_dotplot` 的命名规则。

## 使用示例

### params.json

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "reference": "1",
  "threads": 8,
  "min_block_size": 1,
  "formats": "svg",
  "align_soft": "blast",
  "dbtype": "nucl",
  "cscore": 0.7,
  "dist": 20,
  "iter": 1,
  "figsize": "10x10",
  "dpi": 300
}
```

### 运行

```powershell
main.exe params.json
```

等价的 GenomeLens CLI 命令为：

```powershell
GenomeLens.exe analyze run output\genomelens_request.json
```

## 何时使用

- 需要快速获得两个物种的全局同源关系概览。
- 怀疑存在染色体结构变异、倒位、易位或全基因组复制，需要一张全局图作为初步证据。
- 作为共线性图和核型图的补充，从点矩阵视角验证共线性结果。

## 注意事项

1. 点图只展示**双物种**关系；若输入目录中出现两个以上物种，插件会按 `reference` 与第一个非参考物种生成请求，结果可能不符合预期。
2. `formats` 当前为单选；如需多格式输出，建议分多次运行或直接使用 CLI。
3. `optimize_figsize`、`rewrite_layout_links`、`optimize_karyotype_labels` 是 GenomeLens 扩展参数，不改变 JCVI 核心算法，只影响图件布局和标注。
4. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派，保证命令行参数正确传递。
