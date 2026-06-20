# GenomeLens CLI

## 当前命令树

```powershell
GenomeLens.exe --help
GenomeLens.exe --version
GenomeLens.exe check [-j] [-c <path>] [--jcvi-config <path>] [--install-missing]
GenomeLens.exe config init --workspace <path> [--config-path <path>] [--jcvi-config-path <path>] [--force]
GenomeLens.exe analyze run <request.json> [-j]
GenomeLens.exe analyze mcscan <input-dir> <outdir> [jcvi-config.json] [options] [-j]
GenomeLens.exe analyze template [mcscan]
GenomeLens.exe analyze schema
GenomeLens.exe plot heatmap <matrix.csv> <outdir> [options] [-j]
GenomeLens.exe help [command...]
GenomeLens.exe workbench
GenomeLens.exe clean [--cache] [--all] [--yes]
```

## 推荐入口

交互式命令行优先使用 `analyze mcscan`；外部系统、GUI、插件和批处理系统可以使用 `analyze run <request.json>`。

它要求：

- `input-dir`：输入目录。GenomeLens 会按 basename 自动发现同名物种文件对。
- `outdir`：输出目录。
- `jcvi-config.json`：可选位置参数，也可以改用 `--jcvi-config <path>`。

支持的自动发现输入包括：

- `speciesA.bed` + `speciesA.cds`，以及 `.pep`、`.pep.fa`、`.faa`
- `speciesA.gff3` + `speciesA.fa`

最小示例：

```powershell
GenomeLens.exe analyze mcscan input output --force
```

输出 JSON 摘要：

```powershell
GenomeLens.exe analyze mcscan input output --force -j
```

## 外部 JSON 请求

`analyze run` 读取一个稳定的 `AnalysisRequest` JSON 文件，并复用与 `analyze mcscan` 相同的 dispatcher、方法校验和执行路径。`request.json` 字段与一次成功运行后写入的 `output\inputs\analysis_request.json` 快照一致。

输出 mcscan 请求示例：

```powershell
GenomeLens.exe analyze template mcscan > request.json
```

输出 JSON schema：

```powershell
GenomeLens.exe analyze schema > analysis-request.schema.json
```

最小 `auto_directory` 请求：

```json
{
  "schema_version": 1,
  "kind": "analysis_request",
  "method": "mcscan",
  "input": {
    "mode": "auto_directory",
    "directory": "input"
  },
  "output": {
    "directory": "output",
    "force": true,
    "formats": ["svg"]
  },
  "config": {},
  "options": {
    "preset": "auto",
    "min_block_size": 1
  },
  "method_config": {
    "workflow": "graphics_synteny"
  }
}
```

运行：

```powershell
GenomeLens.exe analyze run request.json
```

## 帮助页

`mcscan` 帮助现在采用分页方式，避免把所有参数堆成一整屏。

```powershell
GenomeLens.exe help analyze mcscan
GenomeLens.exe help analyze mcscan io
GenomeLens.exe help analyze mcscan local
GenomeLens.exe analyze mcscan --help
```

顶层 `help analyze mcscan` 会给出参数页索引；具体分类页通过 `help analyze mcscan <page>` 查看。

## 常用参数

- `-c, --config <path>`：GenomeLens 主配置。
- `--jcvi-config <path>`：JCVI 配置；优先级高于位置参数。
- `--reference <name|index>`：参考物种名称或 1-based 索引。
- `--threads <n>`：线程数。
- `--align-soft {blast,last,diamond_blastp}`：比对后端。
- `--dbtype {nucl,prot}`：序列类型。
- `--cscore <float>`：同源匹配过滤强度。
- `--dist <int>`：共线性锚点间最大基因距离。
- `--iter <int>`：block 过滤迭代次数。
- `--min-block-size <int>`：最小共线性 block 大小。
- `--formats svg,pdf`：输出格式。
- `--jcvi-workflow <name>`：选择 workflow。

## Histogram 直方图

`graphics_histogram` 子任务直接消费数值文件，不走物种目录自动发现：

```powershell
GenomeLens.exe analyze mcscan jcvi graphics_histogram numbers.txt output `
  --histogram-columns 0,1 `
  --histogram-bins 30 `
  --histogram-title "Histogram" `
  --force
```

常用参数：

- `--histogram-inputs <path1,path2,...>`：追加更多数值文件。
- `--histogram-columns <c1,c2,...>`：读取哪些 0-based 列。
- `--histogram-skip <int>`：跳过文件前几行。
- `--histogram-bins <int>`：设置 bin 数。
- `--histogram-vmin <float>` / `--histogram-vmax <float>`：限制数值范围。
- `--histogram-xlabel <text>`：设置 X 轴标签。
- `--histogram-title <text>`：设置图标题。
- `--histogram-base {0,2,10}`：启用对数 X 轴。
- `--histogram-facet`：多序列时分面展示。
- `--histogram-fill <color>`：设置柱体填充颜色。

## 目标基因局部共线性

局部共线性参数仍通过 `analyze mcscan` 传入：

- `--target-genes <id1,id2,...>`
- `--up <int>`
- `--down <int>`
- `--split-targets`
- `--label-targets`

示例：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference subject `
  --target-genes AT1G01010,AT1G01020 `
  --up 20 --down 20 `
  --force
```

## 配置与输出

- 配置文件说明见 [`使用方法/配置文件说明.md`](使用方法/配置文件说明.md)。
- workflow 和局部共线性链路说明见 [`使用方法/JCVI能力与配置.md`](使用方法/JCVI能力与配置.md)。

默认情况下，GenomeLens 会在终端打印人类可读摘要，并把本次归一化请求写到 `output\inputs\analysis_request.json`，把顶层摘要写到 `output\report\run_summary.json`。

## 当前边界

`analyze run` 当前支持 `schema_version = 1` 的 `analysis_request`，首个稳定方法为 `mcscan`。后续方法接入时会扩展同一 request schema。

## 独立绘图：Heatmap 热图

`plot heatmap` 适合直接把矩阵 CSV 渲染成热图，不依赖 `mcscan` 的物种输入模型。

最小示例：

```powershell
GenomeLens.exe plot heatmap expr.csv heatmap-out --formats png --force
```

带列分组、行分组与水平色条：

```powershell
GenomeLens.exe plot heatmap expr.csv heatmap-out `
  --groups `
  --rowgroups rowgroups.tsv `
  --horizontalbar `
  --cmap viridis `
  --formats png `
  --force
```

常用参数：

- `--formats svg,pdf`：输出格式列表。
- `--figsize 8x8`：画布尺寸。
- `--dpi 300`：输出分辨率。
- `--cmap viridis`：matplotlib colormap 名称；默认 `jet`。
- `--groups`：把 CSV 第一行解释为列分组。
- `--rowgroups <path>`：提供行分组文件。
- `--horizontalbar`：改用水平色条。
- `--jcvi-engine <path>`：显式指定 `jcvi-genomelens` 引擎。

输出目录会复用标准 GenomeLens 布局：

- `inputs/input_manifest.json`：写出的 engine manifest。
- `intermediate/jcvi/engine_run_summary.json`：引擎原始摘要。
- `results/figures/`：归档后的最终热图。
- `report/run_summary.json`：CLI 侧统一摘要。
