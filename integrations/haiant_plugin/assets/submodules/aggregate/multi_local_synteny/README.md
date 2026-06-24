# gljcvi-multi-local-synteny — 多物种局部共线性总图插件

## 概述

`gljcvi-multi-local-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**多物种局部共线性总图**原子子模块插件。它把 `params.json` 直接转换为 `analyze submodule jcvi.local_synteny_multi` 调用，不需要生成 `genomelens_request.json`。

> `module_kind = aggregate`。调用方必须先准备好多物种聚合后的 `tracks`、聚合 `blocks`、merged BED 与目标基因列表；该插件不负责 reference-vs-targets 的前置拼装。

该子模块把 reference-vs-targets  pairwise 局部共线性结果聚合成一张多物种总图，适合展示某个目标基因窗口在多个物种中的保守性。

本目录是 `gljcvi-multi-local-synteny` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.local_synteny_multi
```

## 输入端口

| 端口 | 类型 | 说明 |
|------|------|------|
| `tracks` | list | 每个物种的 `{name, bed}` 字典列表 |
| `blocks` | file | 聚合后的多物种 blocks 文件 |
| `bed` | file | 聚合后的多物种 BED 文件 |
| `target_genes` | list | 目标基因 ID 列表 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `tracks` | list/str | 是 | — | 物种轨道列表；字符串时必须是 JSON 数组 |
| `blocks` | file | 是 | — | blocks 文件路径 |
| `bed` | file | 是 | — | BED 文件路径 |
| `target_genes` | list/str | 是 | — | 目标基因 ID 列表；字符串时用逗号分隔 |
| `formats` | enum | 否 | `svg` | 输出格式 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "output_dir": "output",
  "tracks": "[{\"name\": \"reference\", \"bed\": \"reference.bed\"}, {\"name\": \"targetA\", \"bed\": \"targetA.bed\"}]",
  "blocks": "local_synteny_multi.blocks",
  "bed": "local_synteny_multi.bed",
  "target_genes": "gene1,gene2",
  "formats": "svg"
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.local_synteny_multi --input-ports "{\"tracks\": [...], \"blocks\": \"...\", \"bed\": \"...\", \"target_genes\": [...]}" --output-dir output --force
```

## 注意事项

1. `tracks`、`blocks`、`bed`、`target_genes` 必须全部提供。
2. 该插件通常作为 `gljcvi-synteny` 一站式 reference-vs-targets 流程的后续步骤使用，输入由平台聚合生成。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
