# 交付说明

## 交付包

构建脚本会把 release zip 写入 `app/`：

- `GenomeLens-0.9.12.post1-windows-core.zip`
- `GenomeLens-0.9.12.post1-windows-with-toolchains.zip`
- `GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip`
- `GenomeLens-HAIant-plugin-1.0.0.post1.zip`

这些 zip 是构建产物，不进入源码跟踪。

## 当前交付能力

当前交付包面向真实 JCVI 共线性分析：

- 从两个或多个物种的 GFF+FASTA 或 BED+CDS 输入开始，并可按物种混用两类输入。
- 自动调用 BLAST+ 和 `jcvi-genomelens` engine。
- 2 个物种时运行双物种真实流程；3 个及以上物种时自动拆分为 all-vs-all pairwise 并汇总结果。
- 输出 anchors、blocks、dotplot、synteny figure、可选 ortholog 结果，以及多物种 global karyotype 汇总图。
- HAIant plugin 可通过 `params.json` 驱动相同流程，同时兼容新版 `species[]` 和旧版 `query/subject` 参数。

## 已知限制

完整目标中的“跨全部物种的一张最终美化版总图、全局 layout/seqids 自动优化、多物种区块合并/排序/过滤、机器学习评分”尚未完成，因此当前 full/offline package 不应宣称支持最终美化版共线性总图。

ImageMagick 当前为可选工具链；若未随包提供，环境检查会提示 degraded，但不影响已验证的 BLAST/JCVI 核心流程。

## 构建命令

```powershell
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_split_packages.ps1
conda run -n genomelens powershell -NoProfile -ExecutionPolicy Bypass -Command "Push-Location integrations\haiant_plugin; python -m PyInstaller pyinstaller\genomelens_haiant.spec --clean --noconfirm; Pop-Location; .\scripts\build_haiant_plugin.ps1"
```

构建和 smoke test 应使用 `genomelens` conda 环境，解释器版本为 Python 3.12。
