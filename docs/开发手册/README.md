# 开发手册

## 环境

统一使用 `genomelens` conda 环境，Python 3.12：

```powershell
conda activate genomelens
python --version
```

`platform/` 和 `engines/jcvi/` 是两个 editable package，共用同一个解释器环境。

## 当前架构

- `platform/`：平台核心 / CLI 外壳，不直接导入 `jcvi`。
- `engines/jcvi/`：第一个正式引擎，内置 vendored JCVI。
- `engines/`：引擎层目录，未来可平级接入第二个比较基因组学引擎。
- `integrations/haiant_plugin/`：HAIant 插件适配器。
- `gui/`、`agents/`：Tauri GUI 与 Agent 路线图目录（GUI 已实现先行版）。
- `references/`：示例数据与本地参考。
- `toolchains/`：本地运行时缓存，不进入 Git 跟踪。

关键工程文档：

- `开发规范.md`：项目级总纲，覆盖代码、测试、协作、发布与文档。
- `协作开发方案.md`：分支模型、PR 流程与 `main` 分支保护规则。
- `能力接入规则.md`：新增能力时要同步的协议、测试和文档。
- `架构调整/README.md`、`多平台兼容方案.md`、`最终架构目标.md`：平台化与长期架构。
- `AGENTS.md`、`CORE_AGENT.md`（仓库根目录）：AI Agent 工作流与核心职责。

当前实现：

- 双物种真实 JCVI 端到端链路。
- 多物种 all-vs-all pairwise 编排与汇总。
- 以参考物种目标基因为中心的 `local_synteny` 局部共线性链路。
- 由各 pairwise 共线性边聚合出的全局核型总图。

## 测试

```powershell
python -m pytest platform/tests
python -m pytest engines/jcvi/tests
python -m pytest integrations/haiant_plugin/tests
```

完整烟测应覆盖：

- BED+CDS / GFF+FASTA 双物种输入。
- `graphics_synteny`、`graphics_dotplot`、`graphics_karyotype`。
- `catalog_ortholog` 双向 ortholog 输出。
- `local_synteny` 目标基因局部共线性。
- 多物种 all-vs-all pairwise 编排与全局核型总图。
- HAIant plugin 参数翻译。

## 构建

```powershell
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gui.ps1
```

构建输出写入 `app/`，不进入 Git 跟踪。

## GUI 开发

0.9.20 起在 `gui/tauri` 下提供第一个先行 GUI 版本 `JCVI meow`（Tauri v2 + React 18）：

```powershell
cd gui/tauri
corepack enable
pnpm install
pnpm lint
pnpm typecheck
pnpm build:web
```

若本地已安装 Rust 工具链：

```powershell
cargo check --manifest-path src-tauri/Cargo.toml
pnpm tauri build
```

详细说明见 `gui/tauri/README.md` 与 `gui/README.md`。

## Docker 开发环境

0.9.20 起提供 Docker 开发镜像：

```powershell
docker build -t genomelens-dev:0.9.20 .
docker run --rm genomelens-dev:0.9.20 python -m pytest platform/tests -q
```

Docker 镜像不捆绑 BLAST+ / ImageMagick；运行真实分析时需在容器内或宿主机额外配置工具链。
