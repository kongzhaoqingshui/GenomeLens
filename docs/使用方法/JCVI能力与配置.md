# JCVI 能力与配置

## 当前可调度能力

GenomeLens 平台当前把 JCVI 能力分为两类公开入口：

- **一站式工作流**：仅 `synteny`，覆盖从输入发现到 pairwise / 局部共线性 / 多物种聚合出图的全链路。
- **可编排子模块**：10 个原子能力，通过 `SubmoduleRequest` 调用，显式绑定输入端口。

`local_synteny`、`graphics_histogram`、`graphics_heatmap` 不再作为 workflow_id 暴露。局部共线性由 `synteny + target_gene_ids` 自动路由；直方图与热图作为子模块运行。

## 子模块速查

| 子模块 | 说明 |
|---|---|
| `jcvi.mcscan_pairwise` | 执行 BLAST+ 与 JCVI MCscan，输出 anchors、simple blocks 和 blocks。 |
| `jcvi.catalog_ortholog` | 调用 `jcvi.compara.catalog.ortholog --full` 输出双向 ortholog 结果。 |
| `jcvi.graphics_dotplot` | 基于 anchors 输出共线性点图。 |
| `jcvi.graphics_synteny` | 输出 synteny figure（共线性对齐图）。 |
| `jcvi.graphics_karyotype` | 输出 karyotype（核型共线性图）。 |
| `jcvi.graphics_karyotype_global` | 跨全部物种的全局核型总图；`aggregate` 子模块，通常由多物种 `synteny` 自动调度。 |
| `jcvi.graphics_histogram` | 读取数值文件输出直方图，适合 Ks、基因长度、覆盖度等分布检查。 |
| `jcvi.graphics_heatmap` | 从矩阵 CSV 渲染热图，适合表达矩阵、统计矩阵等独立绘图任务。 |
| `jcvi.local_synteny` | 以目标基因为中心绘制双物种局部共线性图。 |
| `jcvi.local_synteny_multi` | 多物种局部共线性总图；`aggregate` 子模块，通常由 `synteny` 自动调度。 |

## 独立热图：`analyze submodule jcvi.graphics_heatmap`

`graphics_heatmap` 不走 `synteny` 的 `species[]` 协议，而是作为独立绘图子模块由 `analyze submodule` 调度。适用场景包括：

- 基因表达矩阵
- 共线性分数矩阵
- 染色体尺度统计量矩阵

命令形态：

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_heatmap `
  --input-ports '{"matrix_csv":"matrix.csv"}' --output-dir output [options]
```

当前支持的公开参数包括：

- `--formats`：输出格式列表，默认继承平台 runtime 或回退到 `svg`。
- `--figsize`：画布尺寸。
- `--dpi`：分辨率。
- `--params '{"cmap":"viridis","groups":true,"rowgroups":"groups.tsv","horizontalbar":true}'`：热图专属参数。

输出目录中会保留：

- `inputs/submodule_request.json`
- `inputs/input_manifest.json`
- `intermediate/jcvi/engine_run_summary.json`
- `results/figures/*.png|*.svg|*.pdf`
- `report/run_summary.json`

## 直方图：`analyze submodule jcvi.graphics_histogram`

`graphics_histogram` 是纯绘图子模块，不要求 `species[]`、BED/CDS 或 GFF/FASTA 输入。它直接读取数值文本文件，并复用 GenomeLens 的 manifest、summary、artifact 归档链路。

常见用法：

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_histogram `
  --input-ports '{"numeric_files":["numbers.txt"]}' --output-dir output `
  --formats png,svg `
  --params '{"columns":[0],"bins":40,"title":"Ks histogram"}' `
  --force
```

补充说明：

- 可通过 `--params '{"columns":[0,1]}'` 从同一个文件中读取多列并叠加/分面展示。
- `--params '{"facet":true}'` 会把多序列拆成多个子图；默认是叠加在同一张图上。
- 当前实现使用 Python/matplotlib 后端，避免依赖未随环境分发的 `Rscript`。

## 一站式流程：多物种局部共线性分析

如果只开放一个入口，建议命名为“GenomeLens 一站式 JCVI 多物种局部共线性分析”。这个入口不是单个 JCVI 命令，而是由平台编排多个 pairwise worker，再由 engine 调用真实 BLAST+ 与 JCVI 完成计算和绘图。

CLI 入口：

```powershell
GenomeLens.exe analyze workflow synteny <input_dir> <output_dir> `
  --reference <ref> --target-genes AT1G01010,AT1G01020 --up 20 --down 20 --force
```

用户视角只需要提供：

- `input_dir`：一个输入文件夹，放入所有物种文件。
- `output_dir`：一个输出目录。
- `reference`：参考物种，默认第一个物种。
- `target_genes`：参考物种中的目标基因 ID。
- `up` / `down`：目标基因上下游窗口大小。

主流程内部包含以下阶段：

1. **输入目录发现**

   GenomeLens 会扫描 `input_dir`，按同名 basename 自动识别物种。当前支持两类输入：

   - `BED + CDS/PEP`：例如 `speciesA.bed` + `speciesA.cds`，也支持 `.pep`、`.pep.fa`、`.faa`。
   - `GFF/GTF + genome FASTA`：例如 `speciesA.gff3` + `speciesA.fa`。

   同一目录允许不同物种使用不同输入模式；同一个物种同时存在两类输入时，优先使用 `BED + CDS/PEP`。

   这一阶段的目标是把用户的一整个输入文件夹转换成稳定的 `species[]` 列表，而不是要求用户手工填写 query/subject。

2. **参数归一化与参考物种选择**

   平台会合并 CLI、配置文件和请求参数，确定参考物种、目标物种列表、线程数、比对后端、共线性参数和绘图参数。多物种局部共线性采用 `reference_vs_targets` 策略：固定一个参考物种，分别与每个目标物种运行局部共线性子任务。

3. **输入校验与工作区创建**

   平台会校验至少存在两个物种、参考物种索引合法、输入文件存在、输出目录可创建，并写出顶层 manifest。顶层 manifest 只描述编排关系；每个 pairwise 子任务会拥有自己的 engine manifest。

4. **注释预处理**

   如果某个物种输入是 `GFF/GTF + FASTA`，平台会先转换为 JCVI 所需的 `BED + CDS`。当前预处理会按代表转录本策略抽取基因模型，尽量统一不同注释来源中的 ID、CDS 和基因坐标。若某个物种已经提供 `BED + CDS/PEP`，则跳过这一步，直接进入 JCVI 链路。

5. **工具链定位**

   平台会定位 `jcvi-genomelens` engine、BLAST+ 的 `blastn` 与 `makeblastdb`，以及按需使用的 LAST / Diamond / ImageMagick 等工具。显式配置优先，其次才回退到环境变量、系统 `PATH`、打包资源或本地缓存。

6. **参考物种对目标物种的 pairwise 编排**

   对于 `reference + N 个目标物种`，平台会创建 N 个 pairwise 子任务：

   ```text
   reference vs target1
   reference vs target2
   reference vs target3
   ...
   ```

   每个子任务独立运行、独立产出 summary，并在顶层 `run_summary.json` 中汇总。单个目标物种失败时，顶层 summary 会记录失败原因，便于用户定位是哪一对物种出了问题。

7. **全基因组同源搜索与 MCscan**

   每个 pairwise 子任务会先运行完整的全基因组同源搜索和 JCVI MCscan：

   - `makeblastdb`：为目标物种序列建库。
   - `blastn` 或其他配置的比对后端：搜索同源匹配。
   - `jcvi.compara.synteny.scan`：从比对结果生成 anchors。
   - `jcvi.compara.synteny.simple`：生成 `.anchors.simple` 简化区块。
   - `jcvi.compara.synteny.mcscan`：生成 `.blocks` 区块轨道。
   - `jcvi.formats.bed.merge`：合并双物种 BED，供后续绘图使用。

   因此，局部共线性并不是只算目标基因附近；它先得到全局 pairwise 共线性基础结果，再从全局结果中截取目标区域。

8. **目标基因窗口截取**

   `local_synteny` 会读取参考物种 BED 顺序，定位 `target_genes` 在参考物种中的基因坐标，并按 `up/down` 截取上下游窗口。随后从完整 `.blocks` 中筛出窗口内仍有目标物种同源关系的区块，形成局部 `.local.blocks`。

   如果启用 `split_targets`，多个目标基因会分别生成局部窗口；否则会合并为一个窗口。`label_targets` 会把目标基因列表传入绘图参数，用于图中标注。

9. **局部 layout 与 JCVI 绘图**

   每个局部窗口会生成自己的：

   - `.local.blocks`
   - `.local.bed`
   - `.local.layout`
   - `.local.svg` / `.local.pdf` 等图件

   绘图阶段调用真实 `jcvi.graphics.synteny`。图件样式参数包括 `figsize`、`dpi`、`glyphstyle`、`glyphcolor`、`shadestyle` 和输出格式。

### 原生 matplotlib 局部共线性渲染器

除默认 JCVI 渲染路径外，`local_synteny` 支持通过 `use_native_local_synteny_renderer: true`（CLI 对应 `--use-native-local-synteny-renderer`）启用原生 matplotlib 渲染器。该渲染器专为跨染色体局部窗口设计，主要差异如下：

- **染色体感知**：每个轨道可按真实染色体拆分成多个 segment，而不是强行压成单一连续区间。
- **间隙压缩**：长锚点-free 区域会被压缩，避免图件被无共线性区域撑开。
- **跨染色体窗口**：参考物种目标基因若落在多条染色体附近，可在同一张图中展示多个染色体 segment。
- **更重计算**：原生渲染器会额外求解 segment 布局、lane 分配与曲线连线，计算成本高于 JCVI 默认路径；建议仅在需要跨染色体视图或默认图件不满足需求时开启。

启用方式：

```powershell
GenomeLens.exe analyze workflow synteny input output `
  --reference subject `
  --target-genes AT1G01010 `
  --use-native-local-synteny-renderer `
  --force
```

或在 `jcvi.config.json` 的 `local_synteny` 分组中设置：

```json
{
  "local_synteny": {
    "use_native_local_synteny_renderer": true
  }
}
```

10. **结果归档与汇总**

    顶层结果会写入：

    - `report/run_summary.json`：平台侧摘要。
    - `inputs/workflow_request.json`：归一化 WorkflowRequest 快照。
    - `results/figures/`：用户可直接查看的归档图件。
    - `intermediate/pairwise/`：每一对 reference-vs-target 子任务的完整中间结果。
    - `intermediate/local/`：局部共线性图件、局部 blocks、局部 bed 和局部 layout。

    一站式入口可以默认把这些结果全部输出，用户后续按需取用；界面不必把每一种中间产物都做成开关。

需要注意：这个主流程的核心产物是“以参考物种目标基因为中心的多物种局部共线性结果”。它会顺带产出 anchors、simple、blocks 等全基因组 pairwise 中间结果，但当前仍不等同于“全局多物种最终美化版共线性图”。全局 layout/seqids 自动优化、跨物种区块合并排序和候选评分仍属于后续能力。

## 能力边界

平台入口已经支持 2 到 n 个物种的 `species[]` 输入，并会把 3 个以上物种自动拆成 all-vs-all pairwise 子任务。所有 pairwise 子任务完成后，会把成功对的共线性边自动聚合成一张全局核型总图（`graphics_karyotype_global`），随 `run_summary.json` 的扩展信息一并输出。

engine 当前仍以 pairwise worker 作为真实 JCVI 调用粒度，但公开 manifest 已升级为 `schema_version=3`：pairwise 输入通过 `inputs.species[0:2]` 表达，`query/subject` 只允许作为 engine 内部局部变量或运行时对象名存在。多物种顶层编排由平台 `WorkflowPlanner` / `PlanExecutor` 汇总。

尚未完成：

- 跨全部物种的一张最终美化版总图。
- 全局 layout/seqids 自动生成和优化。
- 多物种区块合并、排序和过滤。
- 机器学习评分与候选优先级排序。

## 配置文件

GenomeLens V3 把配置拆成两类：

- `genomelens.config.json`：平台配置，例如 workspace、默认输出目录、日志级别、工具链路径、`engine_profile_path`。
- `jcvi.config.json`：engine profile，仅作为 JCVI 分析参数的默认模板。

完整字段说明、默认值、配置示例和环境变量用法见 [`配置文件说明.md`](配置文件说明.md)。下文只保留与 JCVI 能力直接相关的要点。

`analyze workflow`、`analyze submodule` 与 `check` 支持 `--config` 和 `--jcvi-config`，也支持通过 `GENOMELENS_CONFIG` 与 `GENOMELENS_ENGINE_PROFILE` 指向配置文件。旧环境变量 `GENOMELENS_JCVI_CONFIG` 仍会被映射到 `GENOMELENS_ENGINE_PROFILE`。配置优先级固定为：

1. CLI 显式参数
2. 请求 JSON 中的 `parameters` / `runtime`
3. engine profile
4. 平台配置
5. 环境变量
6. 系统 `PATH`
7. 打包资源
8. `toolchains/` 本地缓存

engine profile 中的 `jcvi_engine_path`、`blastn_path`、`makeblastdb_path`、`magick_path`、`threads`、`formats`、`min_block_size`、各分组参数会参与真实运行。

## 降级策略

`allow_simplified_fallback` 是保留协议字段。当前版本不实现简化算法；用户显式开启时会直接报错，避免把非真实 JCVI 结果冒充为正式分析结果。
