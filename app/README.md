# App release artifacts（发布制品）

构建脚本会把 release zip（发布压缩包）写入本目录。这些文件是生成物，不进入 Git 跟踪。

## 0.9.20 产物清单

- `GenomeLens-0.9.20-windows-core.zip`：平台核心包（`GenomeLens.exe` + 引擎，不含外部二进制工具链）。
- `GenomeLens-0.9.20-windows-with-toolchains.zip`：完整离线包，已包含 BLAST+ 与 ImageMagick 工具链。
- `GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip`：独立的 `jcvi-genomelens` 引擎可执行包。
- `gljcvi-auto.zip`：HAIant 智然体自动流插件（对应 `analyze mcscan jcvi` 一键分析）。
- `gljcvi-dotplot.zip`：独立点图插件。
- `gljcvi-synteny.zip`：独立共线性图插件。
- `gljcvi-karyotype.zip`：独立核型图插件。
- `gljcvi-local-synteny.zip`：独立局部共线性插件。
- `gljcvi-catalog-ortholog.zip`：独立双向 ortholog 插件。

## 能力范围

- 从 2 到 n 个物种的 `GFF+FASTA` 或 `BED+CDS` 输入开始，并可按物种混用两类输入。
- 自动调用 BLAST+ 与 `jcvi-genomelens` engine（引擎）。
- 2 个物种时运行双物种真实流程；3 个及以上物种时自动拆分为 all-vs-all pairwise（全组合两两比较）并汇总结果。
- 支持以参考物种目标基因为中心的 `local_synteny` 局部共线性分析。
- 新增 `--use-native-local-synteny-renderer` 原生 matplotlib 局部共线性渲染器（计算较重，默认关闭），支持跨染色体局部窗口。
- 输出 anchors（锚点）、blocks（区块）、dotplot（点图）、synteny figure（共线性图）、karyotype（核型图）、ortholog（同源基因）结果，以及多物种全局核型总图（global karyotype）。
- 首个先行 GUI 版本 `JCVI meow` 位于 `gui/tauri/`，版本号 `0.9.20-preview.1`；CLI 侧入口仍为 `analyze mcscan`。

完整目标中的“跨全部物种的一张最终美化版总图、全局 layout/seqids 自动优化、多物种区块合并/排序/过滤、机器学习评分”尚未完成，因此当前 full/offline package（完整/离线包）不能宣称支持最终美化版共线性图。

## 构建命令

```powershell
# 平台核心 + 工具链分包
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1

# HAIant 功能插件（逐个构建）
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1 -Feature dotplot
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1 -Feature synteny
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1 -Feature karyotype
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1 -Feature local_synteny
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_gljcvi_feature_plugin.ps1 -Feature auto
```

发布时应使用 release attachments（发布附件）、Git LFS 或独立 artifact store（制品库）承载大型 zip。
