# HAIant 插件架构：完全独立的轻量插件

> 本文件描述 GenomeLens 在智然体（HAIant）平台的新插件发布模型。
> GenomeLens 平台与工具链被视为外部软件；每个 HAIant 插件只携带自己的入口与配置，运行时通过 `genomelens_exe`（或 `GENOMELENS_EXE` 环境变量）调用外部 GenomeLens 可执行文件。
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
- 所有插件统一使用 `<genomelens.exe> analyze run <request.json>` 调用 GenomeLens。

---

## 2. 组件定义

### 2.1 外部 GenomeLens 平台

GenomeLens 平台（包含 `GenomeLens-runtime.exe` 或 `genomelens.cmd` / `genomelens.exe` 等入口）是外部软件，不由 HAIant 插件携带。用户需要在 `params.json` 中提供：

```json
{
  "genomelens_exe": "C:/GenomeLens/GenomeLens-runtime.exe"
}
```

也可以通过环境变量指定：

```powershell
$env:GENOMELENS_EXE = "C:\GenomeLens\GenomeLens-runtime.exe"
```

插件优先读取 `params.json` 中的 `genomelens_exe`；未设置时回退到 `GENOMELENS_EXE` 环境变量。

如果 `genomelens_exe` 指向 `.cmd` / `.bat` 文件，插件会自动通过 `cmd.exe /c` 分派，保证命令行参数正确传递。

### 2.2 单功能插件

每个 JCVI 小功能对应一个独立插件包：

- `gljcvi-dotplot` — `workflow = graphics_dotplot`
- `gljcvi-synteny` — `workflow = graphics_synteny`
- `gljcvi-karyotype` — `workflow = graphics_karyotype`
- `gljcvi-catalog-ortholog` — `workflow = catalog_ortholog`
- `gljcvi-local-synteny` — `workflow = local_synteny`

每个包只包含：

```text
gljcvi-dotplot/
├── main.exe                    # 插件入口
├── config.json                 # 该功能专用 HAIant UI 参数
├── params.json                 # 示例参数
├── README.md
├── input/                      # 示例输入
└── output/                     # 结果输出
```

### 2.3 统一自动流插件

`gljcvi-auto` 是一个统一的 MCscan 自动流插件，对应 `analyze mcscan jcvi` 一键分析流程。它固定生成 `workflow = graphics_synteny` 的 AnalysisRequest，运行 pairwise MCscan 并生成共线性图与点图；当填写 `target_gene_ids` 时，平台会自动切换到局部共线性模式（与 CLI 的 `--target-genes` 行为一致）。该插件不再提供 workflow 选择器。

### 2.4 输入约定

所有插件默认使用 `input_dir` 自动发现同名物种文件对（与 `analyze mcscan jcvi` CLI 行为一致）。
如果需要显式指定每个物种的文件，仍可填写 `species` 列表和 `input_mode`（保留兼容）。

---

## 3. 运行流程

1. HAIant 解压插件 zip。
2. 用户填写 `params.json`（至少设置 `genomelens_exe`）。
3. HAIant 调用 `main.exe params.json`。
4. `main.exe` 内的 Python 逻辑：
   - 解析 `params.json`
   - 从 `params.json` 或 `GENOMELENS_EXE` 环境变量解析外部 GenomeLens 可执行文件路径
   - 生成 `output/genomelens_request.json`
   - 调用 `<genomelens_exe> analyze run output\genomelens_request.json`
5. 返回外部 GenomeLens 的退出码。

---

## 4. 请求 JSON 映射

所有插件最终都生成 GenomeLens `AnalysisRequest` JSON，调用 `analyze run`。映射规则参见 `PARAMETER_MAPPING.md`。各插件固定的 `method_config.workflow` 如下：

| 插件 | workflow | 说明 |
|---|---|---|
| `gljcvi-dotplot` | `graphics_dotplot` | 点图 |
| `gljcvi-synteny` | `graphics_synteny` | 共线性图 |
| `gljcvi-karyotype` | `graphics_karyotype` | 核型图 |
| `gljcvi-catalog-ortholog` | `catalog_ortholog` | 双向 ortholog 目录 |
| `gljcvi-local-synteny` | `local_synteny` | 局部共线性 |
| `gljcvi-auto` | `graphics_synteny`（固定） | `analyze mcscan jcvi` 一键自动流；填写 `target_gene_ids` 时切换到局部共线性 |

---

## 5. 环境变量汇总

| 变量 | 设置者 | 使用者 | 说明 |
|---|---|---|---|
| `GENOMELENS_EXE` | 用户或 HAIant | 所有插件 | 外部 GenomeLens 可执行文件路径；`params.json` 中的 `genomelens_exe` 优先级更高 |

旧环境变量 `GENOMELENS_PLUGIN_RUNTIME`、`GLJCVIMCSCAN_HOME` 随重型中心与单包插件一起移除，新插件不再使用。

## 6. 构建与发布

### 6.1 单功能插件

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
```

### 6.2 统一自动流插件

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature auto
```

构建产物位于 `app/gljcvi-<feature>.zip`。

---

## 7. 开发注意事项

1. 所有插件入口必须接收 `params.json` 路径作为唯一命令行参数。
2. `params.json` 中必须提供 `genomelens_exe` 或预先设置 `GENOMELENS_EXE` 环境变量。
3. 必须输出 `run.log` 到 `output_dir/run.log`。
4. 必须使用 `try/except` 捕获异常并写入日志，退出码非 0 表示失败。
5. PyInstaller 打包后使用 `sys._MEIPASS` 定位资源文件。
6. 路径解析以 `params.json` 所在目录为基准，而不是插件 EXE 所在目录。
7. 中英文 UI 字段都需要提供：`label` 为中文，`label_en` 为英文。

---

*本文件随插件体系演进可修订。*
