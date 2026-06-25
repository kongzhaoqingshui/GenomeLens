# GenomeLens

面向 Windows-first 交付的本地比较基因组学平台，当前版本 **v1.0.0-preview-1**，是 1.0.0 正式发布前的预览阶段。

GenomeLens 1.X 的定位：在 Windows 上本地、轻量、快捷、高效、真实地整合 **JCVI 及其扩展的全部能力**，并通过两种互补的方式交付给用户：

1. **一站式工作流（One-Stop Workflow）**：一个命令完成从输入发现、预处理、比对、MCscan 到出图的全链路。
2. **可编排子模块（Composable Sub-Module）**：按需调用单个 JCVI 能力，通过显式输入/输出端口组合，适合脚本、批处理、插件和 GUI 积木式编排。

在此之上，GenomeLens 引入自研优化（如原生共线性渲染器），并计划逐步接入更多现代比较基因组学分析方法。

## 快速开始

### 一站式工作流

```powershell
# 双物种共线性
GenomeLens.exe analyze workflow synteny input output --force

# 多物种 all-vs-all 并汇总全局核型总图
GenomeLens.exe analyze workflow synteny input output --force

# 以参考物种目标基因为中心的局部共线性
GenomeLens.exe analyze workflow synteny input output `
  --reference subject --target-genes AT1G01010 --up 20 --down 20 --force
```

### 可编排子模块

```powershell
# 只跑 MCscan 同源搜索与 block 计算
GenomeLens.exe analyze submodule jcvi.mcscan_pairwise `
  --input-ports '{"species_pair":"input"}' --output-dir output --force

# 只绘制点图（需前置 anchors 产物）
GenomeLens.exe analyze submodule jcvi.graphics_dotplot `
  --input-ports '{"species_pair":"input","anchors":"input/query__subject.anchors"}' `
  --output-dir output --force

# 直方图
GenomeLens.exe analyze submodule jcvi.graphics_histogram `
  --input-ports '{"numeric_files":["numbers.txt"]}' --output-dir output --force
```

### 能力与发现

```powershell
# 列出所有一站式工作流和子模块
GenomeLens.exe workflow list --json

# 查看单个能力元数据（含输入/输出端口、参数）
GenomeLens.exe workflow describe synteny --json
GenomeLens.exe workflow describe jcvi.graphics_histogram --json

# 校验端口绑定是否合法
GenomeLens.exe workflow validate --submodule jcvi.graphics_histogram `
  --ports '{"numeric_files":["numbers.txt"]}' --json
```

## 文档索引

- [`docs/用户手册.md`](docs/用户手册.md)：环境、输入准备、两种用法详解、结果位置。
- [`docs/使用方法/WorkflowRequest JSON.md`](docs/使用方法/WorkflowRequest%20JSON.md)：外部 JSON 请求格式与示例。
- [`docs/使用方法/子模块手册.md`](docs/使用方法/子模块手册.md)：每个子模块的端口、参数与 CLI 示例。
- [`docs/使用方法/工作流组合.md`](docs/使用方法/工作流组合.md)：端口连接与产物复用（面向 GUI/脚本）。
- [`docs/项目介绍.md`](docs/项目介绍.md)：1.X 定位、当前边界与模块职责。
- [`docs/开发手册/README.md`](docs/开发手册/README.md)：开发环境、构建与测试。
- [`docs/TOOLCHAINS.md`](docs/TOOLCHAINS.md)：BLAST+、jcvi-genomelens、ImageMagick 工具链说明。
- [`gui/README.md`](gui/README.md)：GUI 构建说明。

## 核心能力

- **输入灵活**：`GFF+FASTA` 或 `BED+CDS/PEP`，同一目录可按物种混用。
- **比对后端可选**：BLAST+ / LAST / Diamond。
- **JCVI 能力全覆盖**：dotplot、synteny、karyotype、local synteny、ortholog、histogram、heatmap 等。
- **多物种自动编排**：2 个物种走真实双物种流程，3 个及以上自动拆分为 all-vs-all pairwise 并汇总为全局核型总图。
- **自研优化**：原生 `local_synteny_renderer` 支持跨染色体局部窗口，可在 `--use-native-local-synteny-renderer` 下启用。
- **Windows-first 本地交付**：随包工具链、`check --install-missing`、离线包、PowerShell 构建脚本。
- **插件与 GUI**：HAIant 智然体插件入口；先行 GUI 版本 **JCVI meow**。

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
