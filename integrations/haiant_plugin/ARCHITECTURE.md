# HAIant 插件架构：独立插件与 lightweight / aggregate 子模块分层

> 本文件描述 GenomeLens 在智然体（HAIant）平台的新插件发布模型。
> GenomeLens 平台与工具链被视为外部软件；每个 HAIant 插件只携带自己的入口与配置，运行时通过 `GenomeLens_Path`（或 `GENOMELENS_EXE` 环境变量）调用外部 GenomeLens 可执行文件。
> 旧单包插件、重型中心模型以及 `analyze run` + `WorkflowRequest` 工作流插件已被移除，当前所有插件均为独立外部 GenomeLens 调用模型。

---

## 1. 为什么独立

智然体平台对每个插件包的大小、依赖和职责没有强制约束，但项目实际演进中遇到以下问题：

- **单包过大**：一次更新任何小功能都需要重新上传整个 platform + 工具链。
- **插件互相耦合**：重型中心一旦变更，所有子插件都需要同步调整。
- **runtime 路径不统一**：旧模型要求子插件搜索重型中心或依赖环境变量，部署复杂。

独立后：

- 每个插件只携带自己的入口和配置，体积最小。
- GenomeLens 本体与工具链只需在用户环境中安装一次，所有插件共享同一份外部可执行文件。
- 插件之间互不干扰，可以独立迭代、独立打包、独立发布。
- 一站式工作流插件使用 `<genomelens.exe> analyze workflow synteny ...`；可编排子模块插件使用 `<genomelens.exe> analyze submodule <module_id> ...`。

---

## 2. 组件定义

### 2.1 外部 GenomeLens 平台

GenomeLens 平台（包含 `GenomeLens.exe` 或 `genomelens.cmd` / `genomelens.exe` 等入口）是外部软件，不由 HAIant 插件携带。用户需要在 `params.json` 中提供：

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

`gljcvi-synteny` 直接对应 `analyze workflow synteny` 一键分析流程。它根据 `params.json` 动态生成 `output/jcvi.config.json`，然后直接调用外部 GenomeLens：

```powershell
<GenomeLens_Path> analyze workflow synteny <input_dir> <output_dir> --jcvi-config output/jcvi.config.json
```

未填写 `target_gene_ids` 时生成 `workflow = graphics_synteny` 的全局共线性配置；填写 `target_gene_ids` 时自动切换到 `local_synteny`；3 个及以上物种时平台自动拆分为 all-vs-all pairwise 并聚合全局核型总图与多物种局部总图。该插件不再生成 `genomelens_request.json`，也不提供 workflow 选择器。

### 2.3 可编排子模块插件

对应平台 `SubModuleRegistry` 中的 10 个独立子模块，继续分为 8 个 lightweight 与 2 个 aggregate：

| 插件 | 固定 module_id |
|---|---|
| `gljcvi-mcscan-pairwise` | `jcvi.mcscan_pairwise` | lightweight |
| `gljcvi-catalog-ortholog` | `jcvi.catalog_ortholog` | lightweight |
| `gljcvi-dotplot` | `jcvi.graphics_dotplot` | lightweight |
| `gljcvi-synteny-figure` | `jcvi.graphics_synteny` | lightweight |
| `gljcvi-karyotype` | `jcvi.graphics_karyotype` | lightweight |
| `gljcvi-local-synteny` | `jcvi.local_synteny` | lightweight |
| `gljcvi-histogram` | `jcvi.graphics_histogram` | lightweight |
| `gljcvi-heatmap` | `jcvi.graphics_heatmap` | lightweight |
| `gljcvi-global-karyotype` | `jcvi.graphics_karyotype_global` | aggregate |
| `gljcvi-multi-local-synteny` | `jcvi.local_synteny_multi` | aggregate |

这些插件不写 `genomelens_request.json`，而是直接调用：

```powershell
<GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir <output_dir> [--params <json>] [--formats fmt] --force
```

子模块可调参数（如 `figsize`、`dpi`、`cscore` 等）通过 `--params` 转发；图形输出格式通过 `--formats` 转发。具体字段映射见 `PARAMETER_MAPPING.md`。

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

- `gljcvi-synteny` 使用 `input_dir` 自动发现同名物种文件对（与 `analyze workflow synteny` 的目录发现行为一致）。如果需要显式指定每个物种的文件，仍可填写 `species` 列表和 `input_mode`。
- 可编排子模块插件通过 `params.json` 中的显式端口字段接收输入，例如 `species_pair`、`anchors`、`blocks`、`target_genes`、`numeric_files`、`matrix_csv`、`tracks`/`edges`、`bed` 等。
- aggregate 子模块要求调用方已经准备好跨 pair / 跨物种聚合输入，不承担前置 pairwise 产物拼装职责。
- 下游 4 个可视化子模块（`dotplot`、`synteny_figure`、`karyotype`、`local_synteny`）需要用户显式提供上游产物（`.anchors` / `.blocks` / `target_genes`）。一键“从物种目录直接出图”的端到端路径由 `gljcvi-synteny` 一站式工作流承担。

---

## 3. 运行流程

1. HAIant 解压插件 zip。
2. 用户填写 `params.json`（至少设置 `GenomeLens_Path`）。
3. HAIant 调用 `main.exe params.json`。
4. `main.exe` 内的 Python 逻辑：
   - 解析 `params.json`。
   - 从 `params.json` 的 `GenomeLens_Path` 或 `GENOMELENS_EXE` 环境变量解析外部 GenomeLens 可执行文件路径。
   - 对 `gljcvi-synteny`：动态生成 `output/jcvi.config.json`，并调用 `<GenomeLens_Path> analyze workflow synteny <input> <output> --jcvi-config output/jcvi.config.json`。
   - 对可编排子模块插件：调用 `<GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir <output> [--params ...] [--formats ...] --force`。
5. 返回外部 GenomeLens 的退出码。

---

## 4. 请求映射

可编排子模块插件通过 `analyze submodule` 直接传参，不生成旧式 `WorkflowRequest`。`gljcvi-synteny` 一站式工作流插件生成 `jcvi.config.json`。映射规则参见 `PARAMETER_MAPPING.md`。

| 产物路径 | 类型 | workflow / module_id | 说明 |
|---|---|---|---|
| `app/onestop/gljcvi-synteny.zip` | 一站式工作流 | `analyze workflow synteny` | 自动路由 |
| `app/submodules/lightweight/gljcvi-mcscan-pairwise.zip` | 可编排子模块 | `jcvi.mcscan_pairwise` | pairwise block 计算 |
| `app/submodules/lightweight/gljcvi-catalog-ortholog.zip` | 可编排子模块 | `jcvi.catalog_ortholog` | 双向 ortholog 目录 |
| `app/submodules/lightweight/gljcvi-dotplot.zip` | 可编排子模块 | `jcvi.graphics_dotplot` | 双物种点图 |
| `app/submodules/lightweight/gljcvi-synteny-figure.zip` | 可编排子模块 | `jcvi.graphics_synteny` | 双物种共线性图 |
| `app/submodules/lightweight/gljcvi-karyotype.zip` | 可编排子模块 | `jcvi.graphics_karyotype` | 双物种核型图 |
| `app/submodules/lightweight/gljcvi-local-synteny.zip` | 可编排子模块 | `jcvi.local_synteny` | 目标基因局部共线性 |
| `app/submodules/lightweight/gljcvi-histogram.zip` | 可编排子模块 | `jcvi.graphics_histogram` | 数值直方图 |
| `app/submodules/lightweight/gljcvi-heatmap.zip` | 可编排子模块 | `jcvi.graphics_heatmap` | 矩阵热图 |
| `app/submodules/aggregate/gljcvi-global-karyotype.zip` | 可编排子模块 | `jcvi.graphics_karyotype_global` | 全局核型总图 |
| `app/submodules/aggregate/gljcvi-multi-local-synteny.zip` | 可编排子模块 | `jcvi.local_synteny_multi` | 多物种局部总图 |

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
scripts/build_gljcvi_feature_plugin.ps1 -Feature mcscan_pairwise
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
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

*本文件随插件体系演进可修订。*
