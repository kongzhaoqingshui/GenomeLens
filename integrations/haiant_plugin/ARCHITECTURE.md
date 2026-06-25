# HAIant 插件架构：独立插件与 lightweight / aggregate 子模块分层

> 本文件描述 GenomeLens 在智然体（HAIant）平台上的插件组织方式，以及这些插件如何把比较基因组学分析能力交付给最终用户。
> GenomeLens 平台与工具链被视为外部软件；每个 HAIant 插件只携带自己的入口与配置，运行时通过 `GenomeLens_Path`（或 `GENOMELENS_EXE` 环境变量）调用外部 GenomeLens 可执行文件。
> 当前所有插件都构造标准请求 JSON（`WorkflowRequest` 或 `SubmoduleRequest`），然后通过 `analyze run` 调用平台，不再直接拼 `analyze workflow` / `analyze submodule` 命令行。

---

## 1. 为什么采用独立插件

从使用者视角看，HAIant 里的插件应该足够轻、升级简单、功能边界清晰；从维护者视角看，插件不应该把整套平台和工具链反复打包进去。项目演进中，旧模型逐渐暴露出这些问题：

- **单包过大**：一次更新任何小功能都需要重新上传整个 platform + 工具链。
- **插件互相耦合**：重型中心一旦变更，所有子插件都需要同步调整。
- **runtime 路径不统一**：旧模型要求子插件搜索重型中心或依赖环境变量，部署复杂。

改为独立插件后，用户和维护者都会得到更直接的收益：

- 每个插件只携带自己的入口和配置，体积最小。
- GenomeLens 本体与工具链只需在用户环境中安装一次，所有插件共享同一份外部可执行文件。
- 插件之间互不干扰，可以独立迭代、独立打包、独立发布。
- 一站式工作流插件构造 `WorkflowRequest` 并调用 `analyze run`；可编排子模块插件构造 `SubmoduleRequest` 并调用 `analyze run`。

---

## 2. 组件定义

### 2.1 外部 GenomeLens 平台

GenomeLens 平台（包含 `GenomeLens.exe` 或 `genomelens.cmd` / `genomelens.exe` 等入口）被视为外部运行时，不由 HAIant 插件重复携带。这样做的直接意义是：用户只需要安装一次 GenomeLens，本地所有插件即可共享同一套分析能力与工具链。

用户可以在 `params.json` 中显式提供可执行文件路径：

```json
{
  "GenomeLens_Path": "C:/GenomeLens/GenomeLens.exe"
}
```

也可以通过环境变量指定：

```powershell
$env:GENOMELENS_EXE = "C:\GenomeLens\GenomeLens.exe"
```

插件优先读取 `params.json` 中的 `GenomeLens_Path`；未设置时回退到 `GENOMELENS_EXE` 环境变量。

如果 `GenomeLens_Path` 指向 `.cmd` / `.bat` 文件，插件会自动通过 `cmd.exe /c` 分派，保证命令行参数正确传递。

### 2.2 一站式工作流插件

`gljcvi-synteny` 面向“我只想把一组物种扔进去，然后直接拿到可解释的共线性结果”这一类使用方式。它会生成标准工作流请求 `output/workflow_request.json`，然后调用外部 GenomeLens：

```powershell
<GenomeLens_Path> analyze run output/workflow_request.json
```

未填写 `target_gene_ids` 时，它更偏向全局共线性比较；填写 `target_gene_ids` 时，它会转入目标基因驱动的局部共线性分析；当物种数达到 3 个及以上时，平台会自动拆分双物种基础结果并聚合全局核型总图与多物种局部总图。对最终用户来说，这意味着无需手工拼接多步流程，也能直接得到更完整的比较结果。

### 2.3 可编排子模块插件

可编排子模块适合已经知道自己想做哪一步的人，例如“我已经有双物种基础结果了，现在只想出 dotplot”或“我已经聚合好了多物种 tracks/edges，只想出总图”。当前共提供 9 个独立子模块，继续分为 7 个 lightweight 与 2 个 aggregate：

| 插件 | 固定 module_id | 类型 |
|---|---|---|
| `gljcvi-pairwise` | `jcvi.pairwise` | lightweight |
| `gljcvi-dotplot` | `jcvi.graphics_dotplot` | lightweight |
| `gljcvi-synteny-figure` | `jcvi.graphics_synteny` | lightweight |
| `gljcvi-karyotype` | `jcvi.graphics_karyotype` | lightweight |
| `gljcvi-local-synteny` | `jcvi.local_synteny` | lightweight |
| `gljcvi-histogram` | `jcvi.graphics_histogram` | lightweight |
| `gljcvi-heatmap` | `jcvi.graphics_heatmap` | lightweight |
| `gljcvi-global-karyotype` | `jcvi.graphics_karyotype_global` | aggregate |
| `gljcvi-multi-local-synteny` | `jcvi.local_synteny_multi` | aggregate |

这些插件构造 `SubmoduleRequest`，写入 `output/submodule_request.json`，然后调用：

```powershell
<GenomeLens_Path> analyze run output/submodule_request.json
```

对子模块插件来说，核心思想是“显式输入、显式输出、显式控制分析语义”：可调参数写入 `parameters`，端口绑定写入 `inputs`，输出格式写入 `output.formats`。具体字段映射见 `PARAMETER_MAPPING.md`。

每个包只包含：

```text
gljcvi-<feature>/
├── main.exe                    # 插件入口
├── config.json                 # 该功能专用 HAIant UI 参数
├── params.json                 # 示例参数
├── README.md
├── PARAMETER_MAPPING.md
├── input/                      # 示例输入
└── output/                     # 结果输出
```

### 2.4 输入约定

- `gljcvi-synteny` 使用 `input_dir` 自动发现同名物种文件对，适合直接从原始物种目录起步。
- 可编排子模块插件通过 `params.json` 中的显式端口字段接收输入，例如 `species_pair`、`anchors`、`blocks`、`target_genes`、`numeric_files`、`matrix_csv`、`tracks`/`edges`、`bed` 等，适合已经拥有中间结果的场景。
- aggregate 子模块要求调用方已经准备好跨比较对 / 跨物种聚合输入，不承担前置双物种结果拼装职责；它们更像“把前面已经算好的结果汇总成一张总图”。
- 下游 4 个可视化子模块（`dotplot`、`synteny_figure`、`karyotype`、`local_synteny`）需要用户显式提供上游产物（`.anchors` / `.blocks` / `target_genes`）。如果希望“一次性从物种目录直接跑到图”，更推荐使用 `gljcvi-synteny` 一站式工作流。

---

## 3. 运行流程

1. HAIant 解压插件 zip。
2. 用户填写 `params.json`（至少设置 `GenomeLens_Path`）。
3. HAIant 调用 `main.exe params.json`。
4. `main.exe` 内的 Python 逻辑：
   - 解析 `params.json`。
   - 从 `params.json` 的 `GenomeLens_Path` 或 `GENOMELENS_EXE` 环境变量解析外部 GenomeLens 可执行文件路径。
   - 对 `gljcvi-synteny`：构造 `WorkflowRequest`，写入 `output/workflow_request.json`，并调用 `<GenomeLens_Path> analyze run output/workflow_request.json`。
   - 对可编排子模块插件：构造 `SubmoduleRequest`，写入 `output/submodule_request.json`，并调用 `<GenomeLens_Path> analyze run output/submodule_request.json`。
5. 外部 GenomeLens 负责真正执行同源搜索、共线性识别、聚合绘图与结果归档。
6. 返回外部 GenomeLens 的退出码。

---

## 4. 请求映射

所有插件都生成标准请求 JSON，不再直接拼底层分析命令。这样做的好处是：HAIant 插件只负责表单到平台协议的翻译，真正的分析语义统一由 GenomeLens 平台解释。映射规则参见 `PARAMETER_MAPPING.md`。

| 产物路径 | 类型 | 请求文件 | 说明 |
|---|---|---|---|
| `app/onestop/gljcvi-synteny.zip` | 一站式工作流 | `output/workflow_request.json` | 自动路由 |
| `app/submodules/lightweight/gljcvi-pairwise.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种共线性基础结果（`emit_ortholog=true` 时附带双向 ortholog 目录） |
| `app/submodules/lightweight/gljcvi-dotplot.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种点图 |
| `app/submodules/lightweight/gljcvi-synteny-figure.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种共线性图 |
| `app/submodules/lightweight/gljcvi-karyotype.zip` | 可编排子模块 | `output/submodule_request.json` | 双物种核型图 |
| `app/submodules/lightweight/gljcvi-local-synteny.zip` | 可编排子模块 | `output/submodule_request.json` | 目标基因局部共线性 |
| `app/submodules/lightweight/gljcvi-histogram.zip` | 可编排子模块 | `output/submodule_request.json` | 数值直方图 |
| `app/submodules/lightweight/gljcvi-heatmap.zip` | 可编排子模块 | `output/submodule_request.json` | 矩阵热图 |
| `app/submodules/aggregate/gljcvi-global-karyotype.zip` | 可编排子模块 | `output/submodule_request.json` | 全局核型总图 |
| `app/submodules/aggregate/gljcvi-multi-local-synteny.zip` | 可编排子模块 | `output/submodule_request.json` | 多物种局部总图 |

---

## 5. 环境变量汇总

| 变量 | 设置者 | 使用者 | 说明 |
|---|---|---|---|
| `GENOMELENS_EXE` | 用户或 HAIant | 所有插件 | 外部 GenomeLens 可执行文件路径；`params.json` 中的 `GenomeLens_Path` 或 HAIant 注入的 `GenomeLens_Path` 优先级更高 |

旧环境变量 `GENOMELENS_PLUGIN_RUNTIME`、`GLJCVIMCSCAN_HOME` 随重型中心与单包插件一起移除，新插件不再使用。

---

## 6. 构建与发布

### 6.1 一站式工作流插件

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny
```

产物：`app/onestop/gljcvi-synteny.zip`

### 6.2 可编排子模块插件

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature pairwise
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny_figure
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature histogram
scripts/build_gljcvi_feature_plugin.ps1 -Feature heatmap
scripts/build_gljcvi_feature_plugin.ps1 -Feature global_karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature multi_local_synteny
```

产物：

- `app/submodules/lightweight/gljcvi-<feature>.zip`（8 个）
- `app/submodules/aggregate/gljcvi-<feature>.zip`（2 个）

旧产物目录 `app/workflow-plugins/` 与 `app/gljcvi-auto/` 已废弃，构建前应删除。

---

## 7. 开发注意事项

1. 所有插件入口必须接收 `params.json` 路径作为唯一命令行参数。
2. `params.json` 中必须提供 `GenomeLens_Path` 或预先设置 `GENOMELENS_EXE` 环境变量。
3. 必须输出 `run.log` 到 `output_dir/run.log`。
4. 必须使用 `try/except` 捕获异常并写入日志，退出码非 0 表示失败。
5. PyInstaller 打包后使用 `sys._MEIPASS` 定位资源文件。
6. 路径解析以 `params.json` 所在目录为基准，而不是插件 EXE 所在目录。
7. 中英文 UI 字段都需要提供：`label` 为中文，`label_en` 为英文。

---

从维护角度看，这份架构的目标并不是把所有能力塞进 HAIant，而是让 HAIant 插件成为一层轻薄、稳定、可替换的分析入口。

*本文件随插件体系演进可修订。*
