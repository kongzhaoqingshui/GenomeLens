# HAIant 插件资源说明

本目录中的文件用于把 GenomeLens 作为 HAIant/智然体插件交付。

## 文件

- `config.json`：智然体平台表单元数据，包含 2 到 n 个物种的 `species[]` 参数，以及一站式 JCVI 出图入口。
- `params.json`：可运行的双物种示例参数文件。需要多物种分析时，继续向 `species[]` 追加条目。
- `README.md`：插件包维护说明。
- `PARAMETER_MAPPING.md`：新版 `species[]` 参数和旧版 `query/subject` 参数的兼容说明。

## 入口

- `GenomeLens.exe params.json`：按智然体平台参数运行分析。
- `main.exe params.json`：兼容旧平台或旧脚本调用。
- `GenomeLens.exe` 或 `GenomeLens.exe workbench`：进入内置 GenomeLens CLI workbench。
- `GenomeLens.exe check --json`、`GenomeLens.exe analyze template mcscan`、`GenomeLens.exe --help`：透传到内置 runtime。

## 参数兼容

融合版同时支持新版 `species[]` 参数和旧版 `query_*` / `subject_*` 双物种字段。新表单推荐使用 `species[]`，旧任务可继续使用原字段。

插件不会直接拼接旧版 `analyze mcscan` 手动参数；它会先写出 `genomelens_request.json`，再调用 `analyze run <request.json>`。
