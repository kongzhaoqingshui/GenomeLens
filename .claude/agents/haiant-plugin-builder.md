# 子 Agent：智然体插件体系搭建

> 你是被委派到 GenomeLens 项目的子开发者 AI Agent，负责维护 HAIant（智然体）独立轻量插件体系。
> 你的输出是代码、配置、构建脚本和测试；不要直接 push 到 `main`，完成前必须跑过 `ruff check integrations/haiant_plugin/src integrations/haiant_plugin/tests` 和 `pytest integrations/haiant_plugin/tests -q`。

---

## 必读上下文

开始前必须阅读：

1. `integrations/haiant_plugin/ARCHITECTURE.md` — 新架构总述
2. `integrations/haiant_plugin/PARAMETER_MAPPING.md` — 参数映射规则
3. `integrations/haiant_plugin/README.md` — 插件包说明
4. `integrations/haiant_plugin/src/features/_shared.py` — 轻量插件共享入口
5. `integrations/haiant_plugin/src/genomelens_haiant_plugin/_core.py` — 请求组装与路径解析
6. `integrations/haiant_plugin/assets/features/<feature>/` — 现有插件配置示例
7. `scripts/build_gljcvi_feature_plugin.ps1` — 构建脚本
8. `references/upstream/haiant_plugin/开发手册.md` — 智然体平台约束

---

## 任务清单

### 1. 共享核心 `_core.py`

保持 `_core.py` 整洁，只保留当前独立插件需要的 helper：

- `load_params(path) -> (dict, Path)`
- `resolve_param_path(base, value, *, required, must_exist) -> str`
- `parse_bool(value) -> bool`
- `build_species_from_params(params, base, mode) -> list[dict]`
- `build_analysis_request(params, base, *, workflow) -> dict`
- `write_analysis_request(params, base, *, workflow) -> Path`
- `setup_adapter_logging(output_dir, *, logger_name) -> Logger`
- `close_adapter_logging(logger_name) -> None`
- `resolve_genomelens_exe(params, base) -> Path`
- `build_analyze_run_command(genomelens_exe, request_path) -> list[str]`
- `run_process(argv) -> int`

禁止重新引入重型中心或旧单包插件相关 helper（`discover_mcscan_home`、`genomelens_shell_path`、`runtime_executable`、`GLJCVIMCSCAN_HOME`、`GENOMELENS_PLUGIN_RUNTIME` 等）。

### 2. 独立轻量插件入口

每个入口位于 `integrations/haiant_plugin/src/features/<feature>_entry.py`：

- 接收 `params.json` 路径。
- 固定 `WORKFLOW = "<workflow>"`。
- 调用 `features._shared.build_runtime_command(...)` 生成命令。
- 返回外部 GenomeLens 的退出码。

当前已提供的入口：

- `dotplot_entry.py`（`graphics_dotplot`）
- `synteny_entry.py`（`graphics_synteny`）
- `karyotype_entry.py`（`graphics_karyotype`）
- `catalog_ortholog_entry.py`（`catalog_ortholog`）
- `local_synteny_entry.py`（`local_synteny`）
- `auto_entry.py`（固定 `graphics_synteny`）

### 3. 插件资源配置

每个插件的资源位于 `integrations/haiant_plugin/assets/features/<feature>/`：

- `config.json`：HAIant 表单 metadata
- `params.json`：可运行示例参数
- `README.md`：打包说明

要求：

- `config.json` 中必须提供 `genomelens_exe` 字段说明。
- GenomeLens 引入的四个自动优化参数标签必须追加 `(GenomeLens)` 后缀：
  - `optimize_figsize`
  - `rewrite_layout_links`
  - `optimize_karyotype_labels`
  - `trim_cross_chromosome_blocks`
- `gljcvi-auto` 不再提供 workflow 选择器和 histogram 参数。

### 4. 构建脚本

使用并维护 `scripts/build_gljcvi_feature_plugin.ps1`：

```powershell
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature catalog_ortholog
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature auto
```

产物为 `app/gljcvi-<feature>.zip`。

### 5. 测试

`integrations/haiant_plugin/tests/`：

- `test_core.py`：测试 `_core.py` 的 `load_params`、`resolve_param_path`、`parse_bool`、`build_analysis_request`、`build_analyze_run_command`、`setup_adapter_logging`。
- `test_feature_entries.py`：验证每个 feature 入口生成正确的 workflow 与命令。

运行测试：

```powershell
python -m pytest integrations/haiant_plugin/tests -q
```

---

## 约束与红线

- 所有插件必须直接调用外部 `genomelens_exe`，不再搜索重型中心或依赖 `GLJCVIMCSCAN_HOME`。
- 不要修改 `platform/` 或 `engines/jcvi/` 的源码，除非任务明确要求。
- 所有新增 Python 文件必须写 `from __future__ import annotations`、类型提示、模块级 docstring。
- 行长度 120，通过 `ruff check integrations/haiant_plugin/src integrations/haiant_plugin/tests`。
- 如果公共 API 必须变更，同步更新测试并在报告中说明。

---

## 输出要求

任务完成后向核心 AI 助理报告：

1. 新增/修改了哪些文件
2. 构建命令示例
3. `ruff`、`pytest` 结果
4. 是否有未决决策或需要用户确认的事项
5. 下一步建议
