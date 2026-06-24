# HAIant 插件架构：完全独立的轻量插件

> 本文件描述 GenomeLens 在智然体（HAIant）平台的新插件发布模型。
> GenomeLens 平台与工具链被视为外部软件；每个 HAIant 插件只携带自己的入口与配置，运行时通过 `GenomeLens_Path`（或 `GENOMELENS_EXE` 环境变量）调用外部 GenomeLens 可执行文件。
> 旧单包插件与重型中心模型已被移除，当前所有插件均为独立外部 GenomeLens 调用模型。

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
- 常规工作流插件统一使用 `<genomelens.exe> analyze run <WorkflowRequest v2>` 调用 GenomeLens；原子子模块插件使用 `<genomelens.exe> analyze submodule <module_id> ...`；一站式工作流插件使用 `<genomelens.exe> analyze workflow synteny ...`。

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

### 2.3 独立工作流插件

每个 JCVI workflow 对应一个独立插件包：

- `gljcvi-dotplot` — `workflow = graphics_dotplot`
- `gljcvi-synteny-figure` — `workflow = graphics_synteny`
- `gljcvi-karyotype` — `workflow = graphics_karyotype`
- `gljcvi-catalog-ortholog` — `workflow = catalog_ortholog`
- `gljcvi-local-synteny` — `workflow = local_synteny`
- `gljcvi-histogram` — `workflow = graphics_histogram`
- `gljcvi-heatmap` — `workflow = graphics_heatmap`

每个包通过 `features._entry_template` 或专用入口生成 `WorkflowRequest v2`，调用 `analyze run`。

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

### 2.4 原子子模块插件

对应平台 `SubModuleRegistry` 中的独立子模块：

- `gljcvi-mcscan-pairwise` — `jcvi.mcscan_pairwise`
- `gljcvi-global-karyotype` — `jcvi.graphics_karyotype_global`
- `gljcvi-multi-local-synteny` — `jcvi.local_synteny_multi`

这些插件不写 `genomelens_request.json`，而是直接调用：

```powershell
<GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir <output_dir> --force
```

### 2.5 输入约定

工作流插件默认使用 `input_dir` 自动发现同名物种文件对（与 `analyze workflow synteny` 的目录发现行为一致）。如果需要显式指定每个物种的文件，仍可填写 `species` 列表和 `input_mode`。

原子子模块插件通过 `params.json` 中的显式端口字段接收输入，例如 `tracks`/`edges`、`species_pair`、`blocks`/`bed`/`target_genes`。

---

## 3. 运行流程

1. HAIant 解压插件 zip。
2. 用户填写 `params.json`（至少设置 `GenomeLens_Path`）。
3. HAIant 调用 `main.exe params.json`。
4. `main.exe` 内的 Python 逻辑：
   - 解析 `params.json`。
   - 从 `params.json` 的 `GenomeLens_Path` 或 `GENOMELENS_EXE` 环境变量解析外部 GenomeLens 可执行文件路径。
   - 对 `gljcvi-synteny`：动态生成 `output/jcvi.config.json`，并调用 `<GenomeLens_Path> analyze workflow synteny <input> <output> --jcvi-config output/jcvi.config.json`。
   - 对独立工作流插件：生成 `output/genomelens_request.json`（`WorkflowRequest v2`），并调用 `<GenomeLens_Path> analyze run output\genomelens_request.json`。
   - 对原子子模块插件：调用 `<GenomeLens_Path> analyze submodule <module_id> --input-ports <json> --output-dir <output>`。
5. 返回外部 GenomeLens 的退出码。

---

## 4. 请求 JSON 映射

常规工作流插件最终生成 GenomeLens `WorkflowRequest v2` JSON，调用 `analyze run`。原子子模块插件不生成旧 request，而是调用 `analyze submodule`。映射规则参见 `PARAMETER_MAPPING.md`。常规工作流插件会把底层 JCVI workflow 写入 `parameters.extras.engine_workflow`，平台 planner 再映射到引擎 manifest。

| 产物路径 | 类型 | workflow / module_id | 说明 |
|---|---|---|---|
| `app/onestop/gljcvi-synteny.zip` | 一站式工作流 | `analyze workflow synteny` | 自动路由 |
| `app/workflow-plugins/gljcvi-dotplot.zip` | 独立工作流 | `graphics_dotplot` | 点图 |
| `app/workflow-plugins/gljcvi-synteny-figure.zip` | 独立工作流 | `graphics_synteny` | 双物种共线性图 |
| `app/workflow-plugins/gljcvi-karyotype.zip` | 独立工作流 | `graphics_karyotype` | 核型图 |
| `app/workflow-plugins/gljcvi-catalog-ortholog.zip` | 独立工作流 | `catalog_ortholog` | 双向 ortholog 目录 |
| `app/workflow-plugins/gljcvi-local-synteny.zip` | 独立工作流 | `local_synteny` | 局部共线性 |
| `app/workflow-plugins/gljcvi-histogram.zip` | 独立工作流 | `graphics_histogram` | 直方图 |
| `app/workflow-plugins/gljcvi-heatmap.zip` | 独立工作流 | `graphics_heatmap` | 热图 |
| `app/submodules/gljcvi-mcscan-pairwise.zip` | 原子子模块 | `jcvi.mcscan_pairwise` | pairwise block 计算 |
| `app/submodules/gljcvi-global-karyotype.zip` | 原子子模块 | `jcvi.graphics_karyotype_global` | 全局核型总图 |
| `app/submodules/gljcvi-multi-local-synteny.zip` | 原子子模块 | `jcvi.local_synteny_multi` | 多物种局部总图 |

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

### 6.2 独立工作流插件

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny_figure
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature histogram
scripts/build_gljcvi_feature_plugin.ps1 -Feature heatmap
```

产物：`app/workflow-plugins/gljcvi-<feature>.zip`

### 6.3 原子子模块插件

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature mcscan_pairwise
scripts/build_gljcvi_feature_plugin.ps1 -Feature global_karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature multi_local_synteny
```

产物：`app/submodules/gljcvi-<feature>.zip`

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
