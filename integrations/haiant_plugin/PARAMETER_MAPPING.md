# HAIant 参数映射

HAIant 插件把 `params.json` 转换为 GenomeLens `AnalysisRequest` JSON，然后调用外部 GenomeLens 可执行文件：

```powershell
<genomelens_exe> analyze run output\genomelens_request.json
```

所有相对路径都按 `params.json` 所在目录解析。

## 架构说明

当前插件体系为**完全独立的轻量插件**：

- 每个 JCVI 小功能对应一个独立插件包（`gljcvi-dotplot`、`gljcvi-synteny`、`gljcvi-karyotype`、`gljcvi-catalog-ortholog`、`gljcvi-local-synteny`）。
- `gljcvi-auto` 固定对应 `analyze mcscan jcvi` 一键自动流（`workflow = graphics_synteny`）。
- 所有插件都不再依赖重型中心 `gljcvimcscan` 或 `GLJCVIMCSCAN_HOME`。
- 用户需要在 `params.json` 中提供 `genomelens_exe`，或预先设置 `GENOMELENS_EXE` 环境变量。

详见 `ARCHITECTURE.md`。

## 公共字段

| 平台字段 | 类型 | 请求字段 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|---|
| `genomelens_exe` | path | — | 是* | — | 外部 GenomeLens 可执行文件路径（`.exe` / `.cmd` / `.bat`） |
| `input_dir` | dir | `input.species[]`（自动发现） | 是* | — | 自动发现同名物种文件对的输入目录 |
| `species` | array | `input.species[]` | 是* | — | 显式物种列表（与 `input_dir` 二选一） |
| `input_mode` | enum | `input.mode` / 每个物种的 `input_mode` | 否 | `bed_cds` | `bed_cds` 或 `gff_genome` |
| `output_dir` | dir | `output.directory` | 否 | `output` | 结果输出目录 |
| `reference` | str/int | `input.reference_index` | 否 | `1` | 参考物种名称或 1-based 索引 |
| `threads` | int | `options.threads` | 否 | `4` | 运行时工作线程数 |
| `min_block_size` | int | `options.min_block_size` | 否 | `5` | 保留 block 的最小基因数 |
| `formats` | csv/list | `output.formats` | 否 | `png` | 输出格式，如 `png,svg,pdf` |
| `align_soft` | enum | `method_config.align_soft` | 否 | `blast` | 比对后端：`blast` / `last` / `diamond_blastp` |
| `dbtype` | enum | `method_config.dbtype` | 否 | `nucl` | 序列类型：`nucl` / `prot` |
| `cscore` | float | `method_config.cscore` | 否 | `0.7` | 同源匹配过滤强度 |
| `dist` | int | `method_config.dist` | 否 | `20` | 共线性锚点最大基因距离 |
| `iter` | int | `method_config.iter` | 否 | `1` | Block 过滤迭代次数 |
| `glyphstyle` | enum | `method_config.glyphstyle` | 否 | `""` | 基因形状：`box` / `arrow` |
| `glyphcolor` | enum | `method_config.glyphcolor` | 否 | `""` | 基因着色：`orientation` / `orthogroup` |
| `shadestyle` | enum | `method_config.shadestyle` | 否 | `""` | 连线样式：`curve` / `line` |
| `figsize` | str | `method_config.figsize` | 否 | `""` | 画布尺寸，如 `10x5` |
| `dpi` | int | `method_config.dpi` | 否 | `300` | 图片分辨率 |
| `jcvi_engine` | path | `method_config.jcvi_engine` | 否 | `""` | 显式指定 jcvi-genomelens 引擎 |
| `blastn` | path | `method_config.blastn` | 否 | `""` | 显式指定 blastn |
| `makeblastdb` | path | `method_config.makeblastdb` | 否 | `""` | 显式指定 makeblastdb |
| `jcvi_layout` | path | `method_config.jcvi_layout` | 否 | `""` | 可选 JCVI layout 文件 |
| `jcvi_seqids` | path | `method_config.jcvi_seqids` | 否 | `""` | 可选 JCVI seqids 文件 |
| `optimize_figsize` | bool | `method_config.auto_optimization.optimize_figsize` | 否 | `false` | 自动推导图件尺寸（GenomeLens 扩展） |
| `rewrite_layout_links` | bool | `method_config.auto_optimization.rewrite_layout_links` | 否 | `false` | 改写跨轨道 layout 连线（GenomeLens 扩展） |
| `optimize_karyotype_labels` | bool | `method_config.auto_optimization.optimize_karyotype_labels` | 否 | `false` | 优化全局核型标签（GenomeLens 扩展） |
| `trim_cross_chromosome_blocks` | bool | `method_config.auto_optimization.trim_cross_chromosome_blocks` | 否 | `false` | 切除跨染色体 block 行（GenomeLens 扩展） |
| `allow_simplified_fallback` | bool | `method_config.allow_simplified_fallback` | 否 | `false` | 诊断开关；正式流程保持关闭 |

\* `genomelens_exe` 未设置时读取 `GENOMELENS_EXE` 环境变量；`input_dir` 与 `species` 至少提供一个。

## 工作流固定映射

| 插件 | 固定 workflow | 说明 |
|---|---|---|
| `gljcvi-dotplot` | `graphics_dotplot` | 双物种点图 |
| `gljcvi-synteny` | `graphics_synteny` | 双物种共线性图 |
| `gljcvi-karyotype` | `graphics_karyotype` | 双物种核型图 |
| `gljcvi-catalog-ortholog` | `catalog_ortholog` | 双向 ortholog 目录 |
| `gljcvi-local-synteny` | `local_synteny` | 目标基因局部共线性 |
| `gljcvi-auto` | `graphics_synteny` | `analyze mcscan jcvi` 一键自动流 |

## 局部共线性专属字段

仅 `gljcvi-local-synteny` 与 `gljcvi-auto`（填写时）使用：

| 平台字段 | 请求字段 | 说明 |
|---|---|---|
| `target_gene_ids` | `method_config.target_gene_ids` | 目标基因 ID，多个用逗号分隔 |
| `up` | `method_config.up` | 上游窗口基因数 |
| `down` | `method_config.down` | 下游窗口基因数 |
| `split_targets` | `method_config.split_targets` | 多个目标各自出图 |
| `label_targets` | `method_config.label_targets` | 在图中标注目标基因 |

## 输出约定

插件在 `output_dir` 下写入：

```text
output/genomelens_request.json
output/run.log
```

实际调用命令形如：

```powershell
cmd.exe /c C:\GenomeLens\genomelens.cmd analyze run output\genomelens_request.json
```

当 `genomelens_exe` 不是 `.cmd` / `.bat` 时，直接调用可执行文件：

```powershell
C:\GenomeLens\GenomeLens-runtime.exe analyze run output\genomelens_request.json
```
