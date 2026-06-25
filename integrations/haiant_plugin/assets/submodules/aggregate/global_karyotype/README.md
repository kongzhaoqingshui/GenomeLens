# gljcvi-global-karyotype — 多物种全局核型总图插件

## 概述

`gljcvi-global-karyotype` 是 GenomeLens 在 HAIant（智然体）平台上的**多物种全局核型总图**原子子模块插件。它适合把多个物种之间已经整理好的染色体轨道和跨物种连线汇总成一张总览图，用于整体观察保守框架和主要结构差异。

> `module_kind = aggregate`。调用方必须先准备好多物种聚合后的 `tracks` / `edges` 输入；该插件不负责前置 pairwise 结果拼装。

全局核型总图把多个物种的染色体以轨道形式排列，并用连线展示物种间的共线性关系，特别适合在多物种比较里回答“谁和谁在染色体尺度上最接近”“哪些物种共享相似结构骨架”这类问题。

本目录是 `gljcvi-global-karyotype` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.graphics_karyotype_global
```

## 输入端口

该子模块需要显式提供 `tracks` 与 `edges`：

| 端口 | 类型 | 说明 |
|------|------|------|
| `tracks` | list | 每个物种的 `{name, bed}` 字典列表，用于构建多物种染色体骨架 |
| `edges` | list | 物种间共线性边 `{i, j, simple}` 列表，指向 `.simple` 文件，是跨轨道连线的来源 |

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `tracks` | list/str | 是 | — | 物种轨道列表；字符串时必须是 JSON 数组，用于定义每条轨道的名称与 BED 来源 |
| `edges` | list/str | 是 | — | 共线性边列表；字符串时必须是 JSON 数组，用于定义哪些物种轨道之间需要建立连接 |
| `formats` | enum | 否 | `svg` | 输出格式：`svg` / `png` / `pdf` / `eps` / `jpg` |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "output_dir": "output",
  "tracks": "[{\"name\": \"speciesA\", \"bed\": \"A.bed\"}, {\"name\": \"speciesB\", \"bed\": \"B.bed\"}]",
  "edges": "[{\"i\": 0, \"j\": 1, \"simple\": \"A__B.simple\"}]"
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_karyotype_global --input-ports "{\"tracks\": [...], \"edges\": [...]}" --output-dir output --force
```

## 注意事项

1. `tracks` 与 `edges` 必须在 `params.json` 中以 JSON 数组字符串或 JSON 数组形式提供。
2. 该插件依赖上游 pairwise 流程产出的 `.simple` 边文件，通常作为 `gljcvi-synteny` 一站式流的补充产物使用。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
