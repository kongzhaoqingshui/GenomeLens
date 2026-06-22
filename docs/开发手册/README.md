# 开发手册

## 环境

开发环境统一使用 `genomelens` conda 环境，解释器版本为 Python 3.12。

```powershell
conda activate genomelens
python --version
```

`platform/` 和 `engines/jcvi/` 是两个 editable package(可编辑安装包)，但使用同一个解释器环境。

## 当前架构

- `platform/`：GenomeLens shell(外壳) / 平台核心雏形，不直接导入 `jcvi`。包名仍为 `genomelens`。
- `engines/jcvi/`：第一个正式 engine(引擎)，持有 vendored JCVI(随包 JCVI)。包名仍为 `jcvi_genomelens`。
- `engines/`：引擎层目录，未来可平级接入第二个比较基因组学引擎。
- `gui/`、`agents/`：为 Tauri GUI 与 Agent 预留的路线图目录（当前仅占位）。
- `integrations/haiant_plugin/`：HAIant adapter(智然体适配器)。
- `references/`：示例数据与本地参考。`references/upstream/` 是本地上游对照镜像，已不进入 Git 跟踪。
- `toolchains/`：本地 runtime cache(运行时缓存)，不进入 Git 跟踪。

补充文档：

- `架构调整/README.md`：平台化、多平台、Tauri GUI 与 Agent 相关架构文档索引。
- `架构调整/多平台兼容方案.md`：说明共享核心、多平台薄外壳的运行与发布策略。
- `架构调整/最终架构目标.md`：说明平台核心、多引擎、Tauri GUI、深度学习和 Agent 的长期目标。
- `结构优化计划.md`、`项目改进意见.md`：记录已做过的整理和后续待收口事项，偏计划与回顾，不是当前 CLI 的唯一事实来源。
- `协作开发方案.md`：2~3 人核心团队 + 开源贡献者的分支模型、PR 流程与 `main` 分支保护规则。
- `开发规范.md`：项目级总纲，覆盖代码、测试、协作、发布与文档。
- `AGENTS.md`（仓库根目录）：子开发者 AI Agent 的简要工作流。
- `CORE_AGENT.md`（仓库根目录）：核心 AI 助理的权限与职责说明。
- `CLI入口壳设计.md`：平台级 `genomelens` 命令壳设计，用于环境变量隔离与避免子命令冲突。
- `GUI先行开发/README.md`：Tauri GUI 先行开发计划、三人分工、视觉风格、Git 工作流与构建说明。

当前代码实现的是：

- 双物种真实 JCVI 端到端链路。
- 多物种 all-vs-all pairwise(全组合两两比较) 编排与汇总。
- 以参考物种目标基因为中心的 `local_synteny` 局部共线性链路。
- 把成功 pairwise 共线性边聚合成一张全局核型总图（`graphics_karyotype_global`）。

## 测试

```powershell
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

完整烟测应覆盖：

- BED+CDS 双物种输入。
- GFF+FASTA 双物种输入。
- `graphics_synteny` 默认 dotplot + synteny 输出。
- `graphics_dotplot` 独立点图。
- `graphics_karyotype` 独立核型共线性图。
- `catalog_ortholog` 双向 ortholog 输出。
- `local_synteny` 目标基因局部共线性。
- 多物种 all-vs-all pairwise 编排与全局核型总图。
- HAIant plugin(智然体插件) 参数翻译。

## 构建

```powershell
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -Command "Push-Location integrations\haiant_plugin; python -m PyInstaller pyinstaller\genomelens_haiant.spec --clean --noconfirm; Pop-Location; .\scripts\build_haiant_plugin.ps1"
```

构建输出写入 `app/`，不进入 Git 跟踪。

## GUI 开发

0.9.20 起在 `gui/tauri` 下提供第一个先行 GUI 版本 `JCVI meow`（Tauri v2 + React 18）。

```powershell
cd gui/tauri
corepack enable
pnpm install
pnpm lint
pnpm typecheck
pnpm build:web
```

若本地已安装 Rust 工具链，可进一步校验并打包：

```powershell
cargo check --manifest-path src-tauri/Cargo.toml
pnpm tauri build
```

详细能力、端口、构建参数与环境变量见 `gui/tauri/README.md`。

## Docker 开发环境

0.9.20 起提供 Docker 开发镜像，内置 conda Python 环境、Node.js/pnpm 与 Rust，可直接编译 platform、engine 与 GUI。

构建：

```powershell
docker build -t genomelens-dev:0.9.20 .
```

运行并执行测试：

```powershell
docker run --rm genomelens-dev:0.9.20 python -m pytest platform/tests -q
docker run --rm genomelens-dev:0.9.20 python -m pytest engines/jcvi/tests/unit/test_local_synteny_renderer.py -q
```

开发容器启动（挂载源码）：

```powershell
docker run -it --rm -v ${PWD}:/workspace -p 1420:1420 genomelens-dev:0.9.20 bash
```

Docker 镜像不捆绑 BLAST+ / ImageMagick 等外部二进制；运行真实分析时需在容器内或宿主机额外配置工具链。
