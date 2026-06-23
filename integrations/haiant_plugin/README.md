# GenomeLens HAIant plugin（智然体插件）

这一 integration layer（集成层）把 HAIant `params.json` 转换为 GenomeLens `AnalysisRequest`，再调用外部 GenomeLens 可执行文件执行分析。它不实现分析算法，也不直接调用 JCVI。

## 当前范围

- 完全独立的轻量插件，每个 JCVI 小功能一个包：
  - `gljcvi-dotplot` — `graphics_dotplot`
  - `gljcvi-synteny` — `graphics_synteny`
  - `gljcvi-karyotype` — `graphics_karyotype`
  - `gljcvi-catalog-ortholog` — `catalog_ortholog`
  - `gljcvi-local-synteny` — `local_synteny`
  - `gljcvi-auto` — 固定 `graphics_synteny`（`analyze mcscan jcvi` 一键自动流）
- 支持 BED+CDS 或 GFF+基因组 FASTA 输入。
- 支持 `input_dir` 自动发现物种文件对，或显式提供 `species[]` 列表。
- 不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。

## 入口

```powershell
main.exe params.json
```

带 `params.json` 运行时，插件会先写出稳定的 `genomelens_request.json`，再调用外部 GenomeLens：

```powershell
<GenomeLens_Path> analyze run output/genomelens_request.json
```

`GenomeLens_Path` 从 `params.json` 读取，未设置时回退到 `GENOMELENS_EXE` 环境变量。

## 目录

- `ARCHITECTURE.md`：插件架构总述
- `PARAMETER_MAPPING.md`：字段与 `AnalysisRequest` 映射
- `assets/features/<feature>/`：各插件的 `config.json`、`params.json`、`README.md`
- `src/features/`：各插件入口
- `src/genomelens_haiant_plugin/_core.py`：共享请求组装与路径解析

## 构建

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature auto
```

产物位于 `app/gljcvi-<feature>.zip`。
