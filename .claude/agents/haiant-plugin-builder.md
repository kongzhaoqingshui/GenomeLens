# 子 Agent：智然体插件体系搭建

> 你是被委派到 GenomeLens 项目的子开发者 AI Agent，负责把 HAIant（智然体）插件从旧单包模型迁移到**一重型中心 + 多轻量子插件**模型。
> 你的输出是代码、配置、构建脚本和测试；不要直接 push 到 `main`，完成前必须跑过 `ruff`、`pyright`（platform 模块）和 `pytest integrations/haiant_plugin/tests`。

---

## 必读上下文

开始前必须阅读：

1. `integrations/haiant_plugin/ARCHITECTURE.md` — 新架构总述
2. `integrations/haiant_plugin/PARAMETER_MAPPING.md` — 参数映射规则
3. `integrations/haiant_plugin/assets/config.json` 与 `assets/params.json` — 旧单包插件配置示例
4. `integrations/haiant_plugin/src/genomelens_haiant_plugin.py` — 当前插件源码
5. `integrations/haiant_plugin/tests/test_genomelens_haiant_plugin.py` — 当前测试
6. `references/upstream/haiant_plugin/开发手册.md` — 智然体平台约束
7. `.work/decompile/samtools_filtering/reconstructed/alignment_filtering.py` — PyInstaller 插件入口参考实现
8. `scripts/build_haiant_plugin.ps1` — 旧构建脚本
9. `platform/packaging/pyinstaller/genomelens.spec` — GL runtime 打包 spec

---

## 任务清单

### 1. 提取共享库

把 `genomelens_haiant_plugin.py` 中可复用的逻辑拆到 `integrations/haiant_plugin/src/genomelens_haiant_plugin/_core.py`：

- `load_params(path) -> (dict, Path)`
- `resolve_param_path(base, value, *, required, must_exist, fallback_bases) -> str`
- `parse_bool(value) -> bool`
- `build_species_from_params(params, base, mode) -> list[dict]`
- `build_analysis_request(params, base, *, workflow) -> dict`
- `setup_logging(output_dir) -> logging.Logger`
- `resource_path(relative_path) -> str`（兼容 `sys._MEIPASS`）

保持旧 `genomelens_haiant_plugin.py` 的公开 API（`main`、`build_runtime_command`、`write_runtime_request` 等）继续可用，内部改为调用 `_core.py`。

### 2. 实现 `genomelens` 命令壳

创建 `integrations/haiant_plugin/src/genomelens_wrapper.py`：

- 推断 `GENOMELENS_HOME` 为脚本/可执行文件所在目录。
- 设置 `GENOMELENS_TOOLCHAIN_DIR=%GENOMELENS_HOME%\resources\toolchain`。
- 找到同目录下的 `GenomeLens-runtime.exe`。
- 转发所有命令行参数：`GenomeLens-runtime.exe <argv...>`。
- 如果找不到 runtime，打印中文/英文错误并返回非 0 退出码。

### 3. 实现重型中心入口 `gljcvimcscan`

创建 `integrations/haiant_plugin/src/gljcvimcscan_entry.py`：

- 接收 `params.json` 路径。
- 使用 `_core.py` 解析参数。
- 固定 `workflow="local_synteny"`，生成 `genomelens_request.json`。
- 因为重型中心自身携带 runtime，直接调用 `genomelens_wrapper` 的函数或同目录 `genomelens.exe`。
- 输出 `run.log`，返回退出码。

准备重型中心资源：

- `integrations/haiant_plugin/assets/gljcvimcscan/config.json`：只暴露 `local_synteny` 相关参数
- `integrations/haiant_plugin/assets/gljcvimcscan/params.json`：双物种局部共线性示例
- `integrations/haiant_plugin/assets/gljcvimcscan/README.md`

### 4. 实现轻量子插件入口

在 `integrations/haiant_plugin/src/features/` 下为每个 workflow 创建入口：

- `dotplot_entry.py`（`graphics_dotplot`）
- `synteny_entry.py`（`graphics_synteny`）
- `karyotype_entry.py`（`graphics_karyotype`）
- `catalog_ortholog_entry.py`（`catalog_ortholog`）

每个入口必须：

1. 接收 `params.json` 路径。
2. 解析参数。
3. 调用 `discover_mcscan_home()` 定位重型中心：
   - 先读 `GLJCVIMCSCAN_HOME`
   - 再向上搜索 `gljcvimcscan/`
   - 找不到报错
4. 生成对应 workflow 的 `genomelens_request.json`。
5. 调用 `gljcvimcscan\genomelens.exe analyze run <request.json>`。
6. 输出日志并返回退出码。

为每个轻量插件准备：

- `integrations/haiant_plugin/assets/features/dotplot/config.json`
- `integrations/haiant_plugin/assets/features/dotplot/params.json`
- `integrations/haiant_plugin/assets/features/dotplot/README.md`

对其他 workflow 同理。

### 5. 新增构建脚本

- `scripts/build_gljcvimcscan_center.ps1`：
  - 复用 `scripts/build_split_packages.ps1` 的产物
  - 把 `platform/dist/GenomeLens` 复制到重型中心目录
  - 把 `toolchains/` 复制到 `resources/toolchain/`
  - 用 PyInstaller 把 `genomelens_wrapper.py` 打成 `genomelens.exe`
  - 把重型中心 `config.json`、`params.json`、`README.md`、示例输入打包成 `gljcvimcscan.zip`

- `scripts/build_gljcvi_feature_plugin.ps1`：
  - 参数 `-Feature`（dotplot/synteny/karyotype/catalog_ortholog）
  - 用 PyInstaller 把对应 `features/*_entry.py` 打成 `main.exe`
  - 放入对应 `config.json`、`params.json`、`README.md`、示例输入
  - 打包成 `gljcvi-<feature>.zip`

### 6. 补充测试

在 `integrations/haiant_plugin/tests/` 新增：

- `test_core.py`：测试 `_core.py` 的 `load_params`、`resolve_param_path`、`parse_bool`、`build_analysis_request`。
- `test_discovery.py`：测试 `discover_mcscan_home()` 的环境变量路径、父目录搜索、失败报错。
- `test_gljcvimcscan_entry.py`：验证重型中心入口生成的 `genomelens_request.json` 中 `workflow == local_synteny`。
- `test_feature_entries.py`：验证至少一个轻量入口能正确生成对应 workflow 的请求。

运行测试：

```powershell
python -m pytest integrations/haiant_plugin/tests -q
```

---

## 约束与红线

- 不要修改 `platform/` 或 `engines/jcvi/` 的源码。
- 不要删除旧单包插件 `genomelens_haiant_plugin.py` 的公开函数。
- 所有新增 Python 文件必须写 `from __future__ import annotations`、类型提示、模块级 docstring。
- 行长度 120，通过 `ruff check integrations/haiant_plugin/src integrations/haiant_plugin/tests`。
- 如果公共 API 必须变更，同步更新测试并在报告中说明。
- 遇到不确定决策（如 env var 命名、是否保留旧入口）生成 `docs/开发手册/actions/<日期>-<主题>.md` 并暂停等待确认。

---

## 输出要求

任务完成后向核心 AI 助理报告：

1. 新增/修改了哪些文件
2. 构建命令示例
3. `ruff`、`pyright`、`pytest` 结果
4. 是否有未决决策或需要用户确认的事项
5. 下一步建议（例如：补充更多 workflow、废弃旧单包入口、发布测试包）
