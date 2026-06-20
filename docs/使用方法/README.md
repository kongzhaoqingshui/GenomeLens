# 使用方法

当前版本推荐直接使用：

```powershell
GenomeLens.exe analyze mcscan <input-dir> <output-dir> [jcvi-config.json] [options]
```

这条命令支持 2 到 n 个物种：2 个物种时运行双物种真实 JCVI 流程，3 个以上物种时自动拆成 pairwise 子任务并汇总。

## 环境检查

开发环境：

```powershell
conda activate genomelens
python -m genomelens.cli.main check
```

打包运行时：

```powershell
GenomeLens.exe check
GenomeLens.exe check -j
```

## 输入目录

新手优先使用自动目录发现。把同一物种的文件放在同一个输入目录，并保持 basename 一致。

BED + CDS 示例：

```text
input/
  speciesA.bed
  speciesA.cds
  speciesB.bed
  speciesB.cds
  speciesC.bed
  speciesC.cds
```

也支持蛋白序列作为第二个文件：`.pep`、`.pep.fa`、`.faa`。

GFF + FASTA 示例：

```text
input/
  speciesA.gff3
  speciesA.fa
  speciesB.gff3
  speciesB.fa
```

同一个输入目录可以按物种混用两类输入。例如 `speciesA.bed + speciesA.cds` 与 `speciesB.gff3 + speciesB.fa` 可以放在同一目录；GenomeLens 会只预处理 GFF/GTF + FASTA 物种，并把所有物种统一交给 JCVI 链路。若同一个物种同时提供两类文件，自动发现会优先使用已准备好的 `BED + CDS/PEP`。

## 最小运行

```powershell
GenomeLens.exe analyze mcscan input output --force
```

需要原始 JSON 摘要时加 `-j`：

```powershell
GenomeLens.exe analyze mcscan input output --force -j
```

`-j` 只向 stdout 输出 JSON；日志和进度仍写到 stderr。

外部系统、GUI 或批处理可以改用 `AnalysisRequest` JSON：

```powershell
GenomeLens.exe analyze template mcscan > request.json
GenomeLens.exe analyze run request.json
```

请求格式见 [`AnalysisRequest JSON.md`](AnalysisRequest%20JSON.md)。

## 常见场景

GFF + FASTA 输入：

```powershell
GenomeLens.exe analyze mcscan input output --min-block-size 1 --force
```

BED + CDS 输入：

```powershell
GenomeLens.exe analyze mcscan input output --min-block-size 1 --force
```

参考物种局部共线性：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference subject `
  --target-genes AT1G01010 `
  --up 20 --down 20 `
  --force
```

多物种局部共线性：

```powershell
GenomeLens.exe analyze mcscan input output `
  --reference query `
  --target-genes AT1G01010 `
  --up 20 --down 20 `
  --force
```

## workflow

默认 `graphics_synteny` 会输出：

- `dotplot.svg`
- `synteny.svg`
- anchors
- simple blocks
- blocks

也可以通过 `--jcvi-workflow graphics_dotplot` 只生成点图，或通过 `--jcvi-workflow graphics_karyotype` 生成核型共线性图。

指定 `--target-genes` 后，流程会自动进入 `local_synteny`。

## 配置文件

`config init` 会生成：

- `genomelens.config.json`
- `jcvi.config.json`

`jcvi.config.json` 可以通过四种方式提供，优先级从高到低：

1. `--jcvi-config <path>`
2. 位置参数，放在 `output-dir` 之后
3. 输入目录下的 `jcvi.config.json`
4. 当前工作目录下的 `jcvi.config.json`

示例：

```powershell
GenomeLens.exe analyze mcscan input output `
  --jcvi-config workspace\jcvi.config.json `
  --force
```

主配置文件仍通过 `-c, --config` 指定：

```powershell
GenomeLens.exe analyze mcscan `
  -c workspace\genomelens.config.json `
  --jcvi-config workspace\jcvi.config.json `
  input output `
  --force
```

完整字段说明见 [`配置文件说明.md`](配置文件说明.md)。

## 帮助

查看总帮助：

```powershell
GenomeLens.exe --help
```

查看分页帮助：

```powershell
GenomeLens.exe help analyze mcscan
GenomeLens.exe help analyze mcscan local
```

## 结果位置

- `output\report\run_summary.json`
- `output\inputs\analysis_request.json`
- `output\results\figures\`
- `output\intermediate\jcvi\`
- `output\intermediate\local\`
- `output\intermediate\pairwise\`
- `output\inputs\prepared\`

多物种流程会在顶层摘要里写出 `pairwise_jobs`；每个条目对应一组物种对子任务。

## 当前限制

当前已实现 2 到 n 个物种的自动 pairwise 编排与全局核型总图聚合。全局 layout 自动优化、最终美化总图、物种排序推荐和机器学习评分仍属于后续能力。
