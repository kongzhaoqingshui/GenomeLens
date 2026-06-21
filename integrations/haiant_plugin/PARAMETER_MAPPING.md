# HAIant parameter mapping(参数映射)

插件把 HAIant 平台的 `params.json` 转换为 GenomeLens `AnalysisRequest` JSON，再调用 `GenomeLens-runtime.exe analyze run <request.json>`。

插件不直接调用 JCVI，也不拼接旧版 `analyze mcscan` 手动参数。相对输入路径会优先按插件安装根目录解析，找不到时回退到 `params.json` 所在目录，以兼容智然体执行时把参数文件复制到临时目录的场景。

## 推荐字段

| Platform field(平台字段) | Type(类型) | Request field(请求字段) | Required(是否必填) | Default(默认值) |
|---|---|---|---|---|
| `input_mode` | enum | `input.mode` 与每个物种的 `input_mode` | yes | `bed_cds` |
| `species` | array | `input.species[]` | yes | |
| `output_dir` | path | `output.directory` | yes | `output` |
| `workflow` | enum | `method_config.workflow` | no | `graphics_synteny` |
| `threads` | integer | `options.threads` | no | `4` |
| `min_block_size` | integer | `options.min_block_size` | no | `5` |
| `formats` | csv/list | `output.formats` | no | `png` |
| `jcvi_layout` | path | `method_config.jcvi_layout` | no | |
| `jcvi_seqids` | path | `method_config.jcvi_seqids` | no | |
| `allow_simplified_fallback` | boolean | `method_config.allow_simplified_fallback` | no | `false` |

`species` 在 `bed_cds` 模式下使用：

```json
[
  {"name": "speciesA", "bed": "input/a.bed", "cds": "input/a.cds"},
  {"name": "speciesB", "bed": "input/b.bed", "cds": "input/b.cds"}
]
```

`species` 在 `gff_genome` 模式下使用：

```json
[
  {"name": "speciesA", "gff": "input/a.gff3", "genome": "input/a.fa"},
  {"name": "speciesB", "gff": "input/b.gff3", "genome": "input/b.fa"}
]
```

## workflow(工作流)

智然体插件仅暴露一站式 JCVI 出图入口，`workflow` 当前只支持 `graphics_synteny`。该 workflow 会输出 dotplot(点图) 与 synteny figure(共线性图)。`graphics_dotplot`、`graphics_karyotype`、`mcscan_pairwise` 和 `catalog_ortholog` 暂不作为智然体插件入口暴露。

插件会在输出目录写入：

```text
output/genomelens_request.json
```

实际运行命令形如：

```text
GenomeLens-runtime.exe analyze run output/genomelens_request.json
```

## 旧版字段兼容

为了兼容 1.0.0 HAIant 交付包，未提供 `species[]` 时仍可使用双物种字段：

| Platform field(平台字段) | Type(类型) | Request field(请求字段) |
|---|---|---|
| `query_name` | string | `input.species[0].name` |
| `subject_name` | string | `input.species[1].name` |
| `query_bed` / `query_cds` | path | `input.species[0].bed/cds` |
| `subject_bed` / `subject_cds` | path | `input.species[1].bed/cds` |
| `query_gff` / `query_genome` | path | `input.species[0].gff/genome` |
| `subject_gff` / `subject_genome` | path | `input.species[1].gff/genome` |

此外，以下命令会直接透传到内置 runtime，便于在插件包内查看帮助或进入 workbench：

```text
GenomeLens.exe
GenomeLens.exe workbench
GenomeLens.exe check --json
GenomeLens.exe analyze template mcscan
GenomeLens.exe --help
```
