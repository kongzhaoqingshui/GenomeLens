# gljcvi-multi-local-synteny — 多物种局部共线性总图插件

## 概述

`gljcvi-multi-local-synteny` 是 GenomeLens 在 HAIant（智然体）平台上的**多物种局部共线性总图**聚合子模块插件。它适合把某个候选基因窗口在多个物种中的对应局部区域汇总到一张图里，直接比较邻域保守性、片段拆分和结构差异。

> 这是一个 aggregate 子模块。调用方必须先准备好多物种聚合后的 `tracks`、聚合 `blocks`、merged BED 与目标基因列表；该插件不负责“以参考物种为中心、逐个目标物种展开”的前置拼装。

该子模块把“参考物种对多个目标物种”的局部共线性结果聚合成一张多物种总图，适合回答“同一个目标位点在多个基因组里还保留了多少共同结构”这类问题。
运行完成后，通常会得到一张围绕目标位点的多物种局部共线性总图，用于直接比较不同基因组中的邻域保守模式。

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
| `tracks` | list | 每个物种的 `{name, bed}` 字典列表，用于组织多条局部基因轨道 |
| `blocks` | file | 聚合后的多物种 blocks 文件，用于抽取与目标位点相关的连接关系 |
| `bed` | file | 聚合后的多物种 BED 文件 |
| `target_genes` | list | 目标基因 ID 列表 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `tracks` | list/str | 是 | — | 物种轨道列表；字符串时必须是 JSON 数组，用于定义显示名称和 BED 来源 |
| `blocks` | file | 是 | — | blocks 文件路径，是多物种局部总图连接关系的核心输入 |
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

等价平台入口：

```powershell
GenomeLens.exe analyze run output\submodule_request.json
```

## 注意事项

1. `tracks`、`blocks`、`bed`、`target_genes` 必须全部提供。
2. 该插件通常作为 `gljcvi-synteny` 一站式“目标基因驱动多物种局部分析”流程的后续步骤使用，输入由平台聚合生成。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
