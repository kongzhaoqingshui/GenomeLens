# GenomeLens

面向 Windows-first 的本地比较基因组学平台，当前版本 **v0.9.20**。

GenomeLens 1.X 的目标：在 Windows 上本地、轻量、快捷、高效、真实地整合 JCVI 及其扩展的全部能力，同时提供**一站式工作流**与**可编排子模块**两种使用方式。在 JCVI 之上，我们引入自研优化（如原生共线性渲染器），并计划逐步接入更多现代比较基因组学分析方法。

## 两种用法

### 1. 一站式工作流

一个命令跑完从输入发现、预处理、比对、MCscan 到出图的全链路：

```powershell
GenomeLens.exe analyze mcscan jcvi input output --force
```

需要 JSON 摘要时加 `-j`：

```powershell
GenomeLens.exe analyze mcscan jcvi input output --force -j
```

### 2. 可编排子模块

按需调用单个 JCVI 能力或外部 JSON 请求：

```powershell
# JCVI 子任务
GenomeLens.exe analyze mcscan jcvi input output --jcvi-workflow graphics_dotplot --force
GenomeLens.exe analyze mcscan jcvi input output --jcvi-workflow graphics_karyotype --force
GenomeLens.exe analyze mcscan jcvi input output --jcvi-workflow catalog_ortholog --force

# 以目标基因为中心的局部共线性
GenomeLens.exe analyze mcscan jcvi input output --reference subject --target-genes AT1G01010 --up 20 --down 20 --force

# 外部 JSON 请求
GenomeLens.exe analyze run request.json

# 独立绘图
GenomeLens.exe plot heatmap matrix.csv outdir --formats png --force
```

## 核心能力

- **输入灵活**：`GFF+FASTA` 或 `BED+CDS/PEP`，同一目录可按物种混用。
- **比对后端可选**：BLAST+ / LAST / Diamond。
- **JCVI 能力全覆盖**：dotplot、synteny、karyotype、local synteny、ortholog、histogram 等。
- **多物种自动编排**：2 个物种走真实双物种流程，3 个及以上自动拆分为 all-vs-all pairwise 并汇总为全局核型总图。
- **自研优化**：原生 `local_synteny_renderer` 支持跨染色体局部窗口，可在 `--use-native-local-synteny-renderer` 下启用。
- **Windows-first 本地交付**：随包工具链、`check --install-missing`、离线包、PowerShell 构建脚本。
- **插件与 GUI**：HAIant 智然体插件入口；先行 GUI 版本 **JCVI meow**（见 [`gui/README.md`](gui/README.md)）。

## 文档索引

- [`docs/用户手册.md`](docs/用户手册.md)：CLI 命令树、输入准备、常用参数与结果位置。
- [`docs/项目介绍.md`](docs/项目介绍.md)：1.X 定位、当前边界与模块职责。
- [`docs/开发手册/README.md`](docs/开发手册/README.md)：开发环境、构建与测试。
- [`docs/更新计划/更新日志.md`](docs/更新计划/更新日志.md)：版本发布记录。
- [`docs/TOOLCHAINS.md`](docs/TOOLCHAINS.md)：BLAST+、jcvi-genomelens、ImageMagick 工具链说明。
- [`gui/README.md`](gui/README.md)：GUI 构建说明。

## 开发环境

统一使用 `genomelens` conda 环境，Python 3.12：

```powershell
conda activate genomelens
python -m genomelens.cli.main check
python -m pytest platform/tests engines/jcvi/tests integrations/haiant_plugin/tests
```

Docker 开发环境见 [`Dockerfile`](Dockerfile)。

## 模块边界

- `platform/`：CLI、输入校验、预处理、工具链定位、结果归档。
- `engines/jcvi/`：当前唯一正式引擎，内置 vendored JCVI，只暴露 `probe` 和 `run`。
- `integrations/haiant_plugin/`：HAIant 插件适配器。
- `gui/`、`agents/`：路线图预留位置，GUI 已实现先行版。

平台核心不直接导入上游 `jcvi`；跨层通信只通过 `jcvi_engine_manifest.json` 与 `engine_run_summary.json`。

## 许可

GenomeLens 自有代码以 MIT License 授权，全文见 `LICENSE`。

仓库内置的 vendored JCVI（`engines/jcvi/src/jcvi/`）保留其 BSD 风格许可（见 `engines/jcvi/licenses/JCVI-LICENSE.txt`），不受 MIT 覆盖。运行时工具链与 Python 依赖各自适用其上游许可，详见 `NOTICE.md`。
