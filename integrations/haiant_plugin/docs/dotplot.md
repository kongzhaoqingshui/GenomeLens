# gljcvi-dotplot — 双物种点图插件

## 概述

`gljcvi-dotplot` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种点图**插件。它把用户填写的 HAIant `params.json` 翻译成 GenomeLens `AnalysisRequest`，调用外部 `GenomeLens.exe` 执行 `analyze run`，最终生成基于 JCVI `graphics_dotplot` 的双物种同源点图。

点图（dotplot）是经典的全基因组比较基因组学可视化方式：以两个物种的染色体为坐标轴，每个点代表一对同源基因。通过点的分布，研究者可以直观地看到大规模共线性区块、染色体重排、融合、断裂、重复事件以及物种间的线性对应关系。

## 生物学意义

在比较基因组学研究中，点图是最直观、最古老的基因组比对可视化形式之一。

- **共线性区块识别**：沿对角线成簇分布的点即为共线性区块（syntenic blocks），代表两个物种在进化过程中保留的保守基因顺序。
- **染色体演化事件**：偏离对角线的点簇提示染色体倒位（inversion）、易位（translocation）、融合（fusion）或断裂（fission）。
- **全基因组复制（WGD）检测**：在同源多倍体或古多倍体物种中，点图会出现多条平行对角线或网格状模式，是推断多倍化历史的重要依据。
- **近缘物种快速比较**：无需复杂参数，即可获得两个物种整体同源关系的全局视图，适合物种对之间的初步扫描。

## 固定工作流

本插件固定使用 GenomeLens 工作流：

```text
workflow = graphics_dotplot
```

插件内部不会重新实现 BLAST、MCscan 或 JCVI 绘图逻辑，所有计算都由外部 GenomeLens 完成。插件只负责参数翻译、请求组装和调用分派。

## 输入要求

插件通过 `input_dir` 自动发现同名物种文件对，支持以下两种输入模式（同一目录内可混用）：

- **BED + CDS/PEP**：例如 `speciesA.bed` + `speciesA.cds`（也支持 `.pep`、`.pep.fa`、`.faa`）。
- **GFF/GTF + 基因组 FASTA**：例如 `speciesA.gff3` + `speciesA.fa`。

输入目录中应恰好包含 **两个物种** 的文件；插件生成双物种点图请求。

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
| `dbtype` | enum | 否 | `nucl` | 序列类型：`nucl`（核酸）或 `prot`（蛋白） |
| `cscore` | float | 否 | `0.7` | 同源匹配过滤强度 |
| `dist` | int | 否 | `20` | 共线性锚点间最大基因距离 |
| `iter` | int | 否 | `1` | Block 过滤迭代次数 |
| `figsize` | str | 否 | `""` | 画布尺寸，例如 `10x10` |
| `dpi` | int | 否 | `300` | 图片分辨率 |
| `optimize_figsize` | bool | 否 | `false` | 自动推导图件尺寸（GenomeLens 扩展） |
| `rewrite_layout_links` | bool | 否 | `false` | 改写跨轨道 layout 连线（GenomeLens 扩展） |
| `optimize_karyotype_labels` | bool | 否 | `false` | 优化全局核型标签（GenomeLens 扩展） |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`PARAMETER_MAPPING.md`](../PARAMETER_MAPPING.md)。

## 输出产物

插件在 `output_dir` 下生成：

```text
output/
├── genomelens_request.json   # 生成的 AnalysisRequest
├── run.log                   # 运行日志
└── results/figures/          # 最终点图（.svg / .png / .pdf 等）
```

点图文件命名通常形如 `query.subject.dotplot.<formats>`，具体取决于 JCVI 引擎对 `graphics_dotplot` 的命名规则。

## 使用示例

### params.json

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
GenomeLens.exe analyze mcscan jcvi graphics_dotplot input output --force
```

## 何时使用

- 需要快速获得两个物种的全局同源关系概览。
- 怀疑存在染色体结构变异、倒位、易位或全基因组复制，需要一张全局图作为初步证据。
- 作为共线性图（synteny figure）和核型图（karyotype）的补充，从“点矩阵”视角验证共线性结果。

## 注意事项

1. 点图只展示**双物种**关系；若输入目录中出现两个以上物种，插件会按 `reference` 与第一个非参考物种生成请求，结果可能不符合预期。
2. `formats` 当前为单选；如需多格式输出，建议分多次运行或直接使用 CLI。
3. `optimize_figsize`、`rewrite_layout_links`、`optimize_karyotype_labels` 是 GenomeLens 扩展参数，不改变 JCVI 核心算法，只影响图件布局和标注。
4. 若 `genomelens_exe` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派，保证命令行参数正确传递。
