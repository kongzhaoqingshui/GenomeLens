# HAIant 插件架构：一重型中心 + 多轻量子插件

> 本文件描述 GenomeLens 在智然体（HAIant）平台的新插件发布模型。
> 旧模型是把完整 runtime 与单一入口全部打在一个 zip 包里；新模型拆分为：
> - **重型中心 `gljcvimcscan`**：携带完整 GL platform 与工具链
> - **轻量子插件**：每个 JCVI 小功能一个独立插件包，依赖重型中心运行
>
> 旧单包插件仍保留为兼容入口，长期目标逐步迁移到分包模型。

---

## 1. 为什么拆分

智然体平台对每个插件包的大小、依赖和职责没有强制约束，但项目实际演进中遇到以下问题：

- **单包过大**：一次更新任何小功能都需要重新上传整个 platform + 工具链。
- **入口语义单一**：旧入口 `GenomeLens.exe` 只做 `analyze run`，无法为不同 JCVI 能力提供专用 UI。
- **环境变量冲突**：`GENOMELENS_PLUGIN_RUNTIME` 等命名过于通用，容易与其他环境变量混淆。
- **runtime 路径不统一**：子插件无法方便地找到 GL runtime。

拆分后：

- 重型中心只需安装一次，小插件可以独立迭代。
- 每个小插件的 `config.json` 只暴露与该功能相关的参数，UI 更精简。
- `genomelens` 主命令与环境变量壳统一了入口语义。

---

## 2. 组件定义

### 2.1 重型中心：`gljcvimcscan`

`gljcvimcscan` 是一个独立的 HAIant 插件包，主要职责：

- 携带完整 GL platform（`GenomeLens-runtime.exe` 及其依赖）。
- 携带完整工具链（`blast/`、`jcvi-genomelens/`、`imagemagick/`）。
- 提供 `genomelens` 命令壳，设置环境变量后调用 `GenomeLens-runtime.exe`。
- 自身暴露 **JCVI 局部共线性分析**工作流（`local_synteny`）。

典型目录结构：

```text
gljcvimcscan/
├── genomelens.exe              # 环境变量壳 + runtime 转发
├── config.json                 # HAIant UI 元数据（local_synteny）
├── params.json                 # local_synteny 示例参数
├── README.md
├── input/                      # 示例输入
├── output/                     # 结果输出
├── GenomeLens-runtime.exe      # 实际 GL runtime
├── resources/
│   └── toolchain/
│       ├── blast/
│       ├── jcvi-genomelens/
│       └── imagemagick/
└── ...                         # runtime 依赖文件
```

### 2.2 `genomelens` 命令壳

`genomelens.exe`（或 `genomelens.cmd`）是 GL runtime 的**环境变量壳**：

1. 根据自身的绝对路径推断 `GENOMELENS_HOME`（即 `gljcvimcscan` 目录）。
2. 设置 `GENOMELENS_TOOLCHAIN_DIR=%GENOMELENS_HOME%\resources\toolchain`。
3. 转发所有参数给 `%GENOMELENS_HOME%\GenomeLens-runtime.exe`。

这样小插件无需关心 runtime 具体位置，只需调用 `gljcvimcscan\genomelens ...`。

### 2.3 轻量子插件

每个 JCVI 小功能对应一个插件包，例如：

- `gljcvi-dotplot`
- `gljcvi-synteny`
- `gljcvi-karyotype`
- `gljcvi-local-synteny`（可选，也可直接使用重型中心）
- `gljcvi-catalog-ortholog`

每个包只包含：

```text
gljcvi-dotplot/
├── main.exe                    # 插件入口
├── config.json                 # 该功能专用 UI 参数
├── params.json                 # 示例参数
├── README.md
├── input/
└── output/
```

### 2.4 子插件定位重型中心的协议

子插件入口在运行时按以下顺序寻找 `gljcvimcscan`：

1. **环境变量 `GLJCVIMCSCAN_HOME`**：如果存在且指向有效目录，直接使用。
2. **向上搜索 `gljcvimcscan/` 目录**：从子插件根目录开始，向父目录逐级搜索名为 `gljcvimcscan` 的目录，直到磁盘根或找到为止。
3. **报错**：如果都没找到，抛出清晰错误：
   ```text
   未找到 gljcvimcscan 重型中心。请安装 gljcvimcscan 插件，或设置 GLJCVIMCSCAN_HOME 环境变量。
   ```

示例搜索路径（子插件位于 `plugins/gljcvi-dotplot/`）：

```text
plugins/gljcvi-dotplot/                 <- 插件根目录
plugins/gljcvi-dotplot/../gljcvimcscan  <- 先查同级
plugins/gljcvi-dotplot/../../gljcvimcscan
...
```

---

## 3. 运行流程

### 3.1 重型中心自身运行

1. HAIant 解压 `gljcvimcscan.zip`。
2. 用户填写 `params.json`（local_synteny 参数）。
3. HAIant 调用 `gljcvimcscan\genomelens.exe params.json`。
4. `genomelens.exe` 设置 `GENOMELENS_HOME` / `GENOMELENS_TOOLCHAIN_DIR`。
5. 插件 Python 逻辑把 `params.json` 转换为 `genomelens_request.json`。
6. 调用 `GenomeLens-runtime.exe analyze run output\genomelens_request.json`。
7. 返回退出码。

### 3.2 轻量子插件运行

1. HAIant 解压 `gljcvi-dotplot.zip`。
2. 用户填写 `params.json`（dotplot 专用参数）。
3. HAIant 调用 `gljcvi-dotplot\main.exe params.json`。
4. `main.exe` 内的 Python 逻辑：
   - 解析 `params.json`
   - 发现 `gljcvimcscan`（环境变量或父目录搜索）
   - 生成 `genomelens_request.json`（`workflow=graphics_dotplot`）
   - 调用 `gljcvimcscan\genomelens.exe analyze run output\genomelens_request.json`
5. 返回退出码。

---

## 4. 请求 JSON 映射

所有插件最终都生成 GenomeLens `AnalysisRequest` JSON，调用 `analyze run`。映射规则与现有插件一致，区别是按插件固定 `method_config.workflow`：

| 插件 | workflow | 说明 |
|---|---|---|
| `gljcvimcscan` | `local_synteny` | 局部共线性分析 |
| `gljcvi-dotplot` | `graphics_dotplot` | 独立点图 |
| `gljcvi-synteny` | `graphics_synteny` | 共线性总图 |
| `gljcvi-karyotype` | `graphics_karyotype` | 核型共线性图 |
| `gljcvi-catalog-ortholog` | `catalog_ortholog` | 双向 ortholog |
| `gljcvi-local-synteny` | `local_synteny` | 局部共线性（可选） |

公共字段映射参见 `PARAMETER_MAPPING.md`。每个轻量子插件的 `config.json` 只暴露该 workflow 需要的字段。

---

## 5. 环境变量汇总

| 变量 | 设置者 | 使用者 | 说明 |
|---|---|---|---|
| `GENOMELENS_HOME` | `genomelens.exe` 壳 | runtime | GL 安装根目录 |
| `GENOMELENS_TOOLCHAIN_DIR` | `genomelens.exe` 壳 | runtime | 工具链根目录 |
| `GLJCVIMCSCAN_HOME` | 用户或 HAIant | 轻量子插件 | 显式指定重型中心位置 |

> 旧插件使用的 `GENOMELENS_PLUGIN_RUNTIME` 在新模型中由 `genomelens` 壳替代，逐步废弃。

---

## 6. 构建与发布

### 6.1 重型中心 `gljcvimcscan`

1. 先运行 `scripts/build_split_packages.ps1` 得到完整 `platform/dist/GenomeLens`。
2. 把 `platform/dist/GenomeLens` 复制到 `gljcvimcscan/` 下作为 runtime。
3. 把工具链复制到 `gljcvimcscan/resources/toolchain/`。
4. 生成 `genomelens.exe`（PyInstaller 包装 `genomelens_wrapper.py`）。
5. 放入 `config.json`、`params.json`、`README.md`、示例输入。
6. 打包为 `gljcvimcscan.zip`。

### 6.2 轻量子插件

1. 为每个 workflow 写一个 `main.py` 入口，调用共享库 `_core.py`。
2. PyInstaller 打包为 `main.exe`。
3. 准备该 workflow 专用的 `config.json`、`params.json`、`README.md`。
4. 不携带任何 runtime 或工具链。
5. 打包为 `gljcvi-<feature>.zip`。

### 6.3 推荐脚本

- `scripts/build_gljcvimcscan_center.ps1`：构建重型中心
- `scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot`：构建单个子插件
- `scripts/build_haiant_plugin.ps1`：保留旧单包构建（兼容过渡期）

---

## 7. 兼容性

- 旧单包插件（`GenomeLens-HAIant-plugin-*.zip`）继续维护，直到所有用户迁移完成。
- 旧插件中的 `GENOMELENS_PLUGIN_RUNTIME` 环境变量仍支持，但新插件优先使用 `genomelens` 壳。
- 重型中心 `gljcvimcscan` 和旧单包插件可以共存，但用户不应同时依赖两套入口。

---

## 8. 开发注意事项

1. 所有插件入口必须接收 `params.json` 路径作为唯一命令行参数。
2. 必须输出 `run.log` 到 `output_dir/run.log`。
3. 必须使用 `try/except` 捕获异常并写入日志，退出码非 0 表示失败。
4. PyInstaller 打包后使用 `sys._MEIPASS` 定位资源文件。
5. 路径解析以 `params.json` 所在目录为基准，而不是插件 EXE 所在目录。
6. 中英文 UI 字段都需要提供。

---

*本文件随插件体系演进可修订。*
