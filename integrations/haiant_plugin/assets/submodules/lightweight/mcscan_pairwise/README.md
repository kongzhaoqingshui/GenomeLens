# gljcvi-mcscan-pairwise — 双物种 MCscan Pairwise 子模块插件

## 概述

`gljcvi-mcscan-pairwise` 是 GenomeLens 在 HAIant（智然体）平台上的**双物种 MCscan pairwise** 原子子模块插件。它把 `params.json` 直接转换为 `analyze submodule jcvi.mcscan_pairwise` 调用，不需要生成 `genomelens_request.json`。

该子模块对两个物种执行同源搜索、锚点扫描与 block 计算，输出 blast table、anchors、simple、blocks 等中间产物，可作为更复杂流程的输入。

本目录是 `gljcvi-mcscan-pairwise` 插件包内容：

- `config.json`：HAIant 表单元数据。
- `params.json`：可运行的示例参数。
- `README.md`：本说明文档。

插件本身不携带 GenomeLens 运行时或工具链，需单独安装 GenomeLens 并提供可执行文件路径。

## 固定子模块

```text
module_id = jcvi.mcscan_pairwise
```

## 输入端口

| 端口 | 类型 | 说明 |
|------|------|------|
| `species_pair` | dir | 包含两个物种文件对的输入目录 |

插件会自动把 `input_dir` 映射到 `species_pair` 端口。

## 主要参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `GenomeLens_Path` | file | 是* | — | 外部 GenomeLens 可执行文件路径 |
| `input_dir` | dir | 是 | — | 输入目录，自动发现物种文件对 |
| `output_dir` | dir | 否 | `output` | 结果输出目录 |
| `align_soft` | enum | 否 | `blast` | 比对后端：`blast` / `last` / `diamond_blastp` |
| `dbtype` | enum | 否 | `nucl` | 序列类型：`nucl` / `prot` |
| `cscore` | float | 否 | `0.7` | 同源匹配过滤强度 |
| `dist` | int | 否 | `20` | 共线性锚点间最大基因距离 |
| `iter` | int | 否 | `1` | Block 过滤迭代次数 |
| `min_block_size` | int | 否 | `1` | 保留 block 的最小基因数 |
| `threads` | int | 否 | `4` | 运行时线程数 |
| `formats` | enum | 否 | `svg` | 输出格式 |

\* `GenomeLens_Path` 未设置时读取 `GENOMELENS_EXE` 环境变量。

完整字段映射参见 [`../../PARAMETER_MAPPING.md`](../../PARAMETER_MAPPING.md)。

## 使用示例

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe",
  "input_dir": "input",
  "output_dir": "output",
  "align_soft": "blast",
  "dbtype": "nucl",
  "cscore": 0.7,
  "dist": 20,
  "iter": 1,
  "min_block_size": 1,
  "threads": 8,
  "formats": "svg"
}
```

```powershell
main.exe params.json
```

等价 CLI：

```powershell
GenomeLens.exe analyze submodule jcvi.mcscan_pairwise --input-ports "{\"species_pair\": \"input\"}" --output-dir output --params "{...}" --formats svg --force
```

## 注意事项

1. 输入目录必须恰好包含两个物种的文件对。
2. 该子模块只输出中间产物和图件，不生成 `genomelens_request.json`。
3. 若 `GenomeLens_Path` 指向 `.cmd` / `.bat`，插件会自动通过 `cmd.exe /c` 分派。
