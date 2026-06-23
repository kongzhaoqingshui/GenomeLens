# GenomeLens 0.9.20 Release Notes

> **说明**：本文档与 `docs/更新计划/更新日志.md` 的 0.9.20 章节内容一致，保留在此处作为历史归档。

---

**Version:** 0.9.20  
**Tag:** [`v0.9.20`](https://github.com/nhAirsy/GenomeLens/releases/tag/v0.9.20)  
**Release Date:** 2026-06-23

---

## 重要更新

0.9.20 是 GenomeLens 首个“重要更新”，从单一 CLI 工具演进为“CLI + 原生渲染 + GUI 先行版 + 容器化开发环境”的多形态交付。

### 新增

- **原生 matplotlib 局部共线性渲染器**：支持染色体感知、间隙压缩与跨染色体局部窗口，解决默认 JCVI 渲染器在跨染色体场景下强行压缩为单一连续区间的问题。
- **独立 CLI 参数 `--use-native-local-synteny-renderer`**：位于 `analyze mcscan` 的 local 参数组，独立于 `auto_optimization` 自动优化组；默认关闭，计算较重。
- **第一个先行 GUI 版本 `JCVI meow`**：基于 Tauri v2 + React 18 的桌面壳与分析向导首屏，版本号 `0.9.20-preview.1`。
- **GenomeLens 开发环境 Docker 镜像**：新增 `Dockerfile` 与 `.dockerignore`，内置 conda Python 3.12、platform/engine editable install、Node.js/pnpm 与 Rust 工具链。

### 变更 / 项目收尾

- `main` 已使用渲染器分支干净覆盖，GUI 分支 `origin/gui/feature/jcvi-meow-baseline` 已合并。
- 文档统一：CLI、配置、JCVI 能力、开发手册、更新日志、GUI README 全部同步。
- 更新日志结构优化：自 0.9.20 起区分“重要更新”与“普通更新”。
- 项目自有源码补充了中文模块/函数 docstring 与 region 注释（vendored JCVI 源码除外）。
- 保留诊断开关 `allow_simplified_fallback`，正式流程会拒绝简化降级。

### 构建产物

重新打包 0.9.20 全部产物，并清理了 `app/` 与 `.build/` 中的 0.9.17/0.9.18/0.9.19 旧 staging 目录、过期 ZIP 与测试数据。

---

## 安装包清单

| 文件名 | 说明 |
|--------|------|
| `GenomeLens-0.9.20-windows-core.zip` | 平台核心包（`GenomeLens.exe` + `jcvi-genomelens` 引擎，不含外部二进制） |
| `GenomeLens-0.9.20-windows-with-toolchains.zip` | 完整离线包，已内置 BLAST+ 与 ImageMagick |
| `GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip` | 独立引擎可执行包 |
| `gljcvi-auto.zip` | HAIant 智然体自动流插件 |
| `gljcvi-dotplot.zip` | 独立点图插件 |
| `gljcvi-synteny.zip` | 独立共线性图插件 |
| `gljcvi-karyotype.zip` | 独立核型图插件 |
| `gljcvi-local-synteny.zip` | 独立局部共线性插件 |
| `gljcvi-catalog-ortholog.zip` | 独立双向 ortholog 插件 |

---

## 快速开始

```powershell
# 解压完整离线包
Expand-Archive GenomeLens-0.9.20-windows-with-toolchains.zip -DestinationPath GenomeLens-0.9.20

# 查看版本
GenomeLens-0.9.20\GenomeLens.exe --version

# 运行示例分析
GenomeLens-0.9.20\GenomeLens.exe analyze mcscan input output --force

# 启用原生局部共线性渲染器
GenomeLens-0.9.20\GenomeLens.exe analyze mcscan input output `
  --reference subject `
  --target-genes AT1G01010 `
  --use-native-local-synteny-renderer `
  --force
```

---

## 验证摘要

- `ruff check` / `ruff format --check`：通过
- `pyright platform/src/genomelens engines/jcvi/src/jcvi_genomelens integrations/haiant_plugin/src`：0 errors
- `pytest` 全量测试：206 passed

---

## 已知限制

- GUI 为 0.9.20 先行预览版，当前完成桌面壳、分析向导首屏与请求草案模型；真实分析仍调用 CLI。
- Docker 开发镜像不捆绑 BLAST+ / ImageMagick，真实分析时需在容器内或宿主机额外配置。
- 全局多物种最终美化版总图、全局 layout/seqids 自动生成与优化、多物种区块合并/排序/过滤、机器学习评分仍在后续路线图中。
