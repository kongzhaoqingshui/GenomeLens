# GenomeLens CLI

## 当前命令树

```powershell
GenomeLens.exe --help
GenomeLens.exe --version
GenomeLens.exe check [-j] [-c <path>] [--jcvi-config <path>] [--install-missing]
GenomeLens.exe config init --workspace <path> [--config-path <path>] [--jcvi-config-path <path>] [--force]
GenomeLens.exe analyze run <request.json> [-j]
GenomeLens.exe analyze mcscan <input-dir> <outdir> [jcvi-config.json] [options] [-j]
GenomeLens.exe help [command...]
GenomeLens.exe workbench
GenomeLens.exe clean [--cache] [--all] [--yes]
```

## 推荐入口

人工命令行推荐入口是 `analyze mcscan`。

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

插件、GUI 和批处理系统可以使用稳定请求入口：

```powershell
GenomeLens.exe analyze run request.json
```

`request.json` 使用 `AnalysisRequest` 协议，字段与运行后写入的 `output\inputs\analysis_request.json` 快照一致。

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
- `--formats png,pdf`：输出格式。
- `--jcvi-workflow <name>`：选择 workflow。

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

`analyze run <request.json>` 已重新开放，用于消费完整 `AnalysisRequest`。`analyze template` 仍未重新开放；需要模板时可参考一次成功运行后的 `output\inputs\analysis_request.json`。
