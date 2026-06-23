# GenomeLens

面向 Windows 的比较基因组学与共线性分析命令行产品，当前版本 **v0.9.20**。

项目完整目标：从 2 到任意多个物种的 GFF/GTF（注释文件）与 FASTA（基因组序列）出发，经过统一参数预设、输入预处理、JCVI 分析与 JCVI 绘图，最终生成可发表、可美化的多物种共线性图。

## 核心能力

- `GFF+FASTA` 或 `BED+CDS/PEP` 输入（支持 `.pep`、`.faa`），同一目录可按物种混用两类输入。
- GFF/GTF 与 FASTA 预处理为 JCVI 所需的 BED/CDS。
- BLAST+ / LAST / Diamond 比对后端可选。
- JCVI MCscan 共线性扫描与 `graphics.dotplot`、`graphics.synteny`、`graphics.karyotype` 出图。
- `catalog.ortholog --full` 双向同源基因结果。
- 以目标基因为中心的 `local_synteny` 工作流。
- 多物种 all-vs-all pairwise 编排与全局核型总图聚合。
- HAIant 智然体插件入口。
- 先行 GUI 版本 **JCVI meow**（见 [`gui/README.md`](gui/README.md)）。

## 快速开始

```powershell
GenomeLens.exe analyze mcscan jcvi input output --force
```

需要 JSON 摘要时加 `-j`：

```powershell
GenomeLens.exe analyze mcscan jcvi input output --force -j
```

检查环境：

```powershell
GenomeLens.exe check
```

## 文档索引

- [`docs/用户手册.md`](docs/用户手册.md)：CLI 命令树、参数参考、输入目录、配置文件与结果位置。
- [`docs/项目介绍.md`](docs/项目介绍.md)：项目目标、当前边界与模块职责。
- [`docs/开发手册/README.md`](docs/开发手册/README.md)：开发环境、构建与测试入口。
- [`docs/更新计划/更新日志.md`](docs/更新计划/更新日志.md)：版本发布记录。
- [`docs/TOOLCHAINS.md`](docs/TOOLCHAINS.md)：BLAST+、jcvi-genomelens、ImageMagick 工具链说明。
- [`gui/README.md`](gui/README.md)：GUI 构建说明。

## 开发环境

统一使用 `genomelens` conda 环境，解释器版本 Python 3.12。

```powershell
conda activate genomelens
python -m genomelens.cli.main check
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

也支持 Docker 开发环境，详见 `Dockerfile`。

## 模块边界

- `platform/`：CLI、输入校验、预处理、工具链定位、manifest 写入、engine 调用与结果归档。
- `engines/jcvi/`：当前唯一正式引擎，持有 vendored JCVI 源码，只暴露 `probe` 和 `run` 两个稳定入口。
- `integrations/haiant_plugin/`：HAIant 插件适配器，读取 `params.json` 并转换为 GenomeLens 请求。
- `gui/`、 `agents/`：路线图预留位置，GUI 已实现先行版。

平台核心不直接导入上游 `jcvi`；跨层通信只通过 `jcvi_engine_manifest.json` 与 `engine_run_summary.json`。

## 许可

GenomeLens 自有代码以 MIT License 授权，全文见 `LICENSE`。

仓库还内置了 vendored JCVI（`engines/jcvi/src/jcvi/`），它保留自己的 BSD 风格许可（见 `engines/jcvi/licenses/JCVI-LICENSE.txt`），**不受 MIT 覆盖**。运行时工具链（BLAST+、ImageMagick）与 Python 运行期依赖各自适用其上游许可。第三方组件与许可边界详见 `NOTICE.md`。
