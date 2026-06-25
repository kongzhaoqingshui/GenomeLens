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
- `coerce_submodule_params(raw, base, declared) -> dict`
- `write_request_json(output_dir, request, *, filename) -> Path`
- `build_run_command(genomelens_exe, request_path) -> list[str]`
- `build_workflow_request(params, base, output_dir) -> dict`
- `build_workflow_runtime_command(genomelens_exe, params, base, output_dir) -> list[str]`
- `build_submodule_request(module_id, inputs, parameters, output_dir, *, formats, threads, force) -> dict`
- `build_submodule_runtime_command(genomelens_exe, *, module_id, inputs, parameters, output_dir, ...) -> list[str]`
- `setup_adapter_logging(output_dir, *, logger_name) -> Logger`
- `close_adapter_logging(logger_name) -> None`
- `resolve_genomelens_exe(params, base) -> Path`

禁止重新引入重型中心或旧单包插件相关 helper（`discover_mcscan_home`、`genomelens_shell_path`、`runtime_executable`、`GLJCVIMCSCAN_HOME`、`GENOMELENS_PLUGIN_RUNTIME`、`build_mcscan_jcvi_command` 等）。

### 2. 独立轻量插件入口

每个入口位于 `integrations/haiant_plugin/src/features/<area>/<feature>_entry.py`：

- 接收 `params.json` 路径。
- 调用 `_core.py` 生成 `analyze run` 命令。
- 返回外部 GenomeLens 的退出码。

当前已提供的入口：

**一站式工作流**

- `onestop/synteny_entry.py`（`analyze workflow synteny`）

**可编排子模块插件（`analyze run` + `SubmoduleRequest`）**

- `submodules/lightweight/pairwise_entry.py`（`jcvi.pairwise`）
- `submodules/lightweight/dotplot_entry.py`（`jcvi.graphics_dotplot`）
- `submodules/lightweight/synteny_figure_entry.py`（`jcvi.graphics_synteny`）
- `submodules/lightweight/karyotype_entry.py`（`jcvi.graphics_karyotype`）
- `submodules/lightweight/local_synteny_entry.py`（`jcvi.local_synteny`）
- `submodules/lightweight/histogram_entry.py`（`jcvi.graphics_histogram`）
- `submodules/lightweight/heatmap_entry.py`（`jcvi.graphics_heatmap`）
- `submodules/aggregate/global_karyotype_entry.py`（`jcvi.graphics_karyotype_global`）
- `submodules/aggregate/multi_local_synteny_entry.py`（`jcvi.local_synteny_multi`）

> 注意：`jcvi.mcscan_pairwise` 与 `jcvi.catalog_ortholog` 已合并为 `jcvi.pairwise`；`emit_ortholog=true` 控制是否输出双向 ortholog 目录。

### 3. 插件资源配置

每个插件的资源位于 `integrations/haiant_plugin/assets/<area>/<kind>/<feature>/`：

- `config.json`：HAIant 表单 metadata
- `params.json`：可运行示例参数
- `README.md`：打包说明

其中 area 为 `onestop` 或 `submodules`，kind 为 `lightweight` 或 `aggregate`。

要求：

- `config.json` 中必须说明 `GenomeLens_Path` 的用途。
- GenomeLens 引入的自动优化参数标签必须追加 `(GenomeLens)` 后缀：
  - `optimize_figsize`
  - `rewrite_layout_links`
  - `optimize_karyotype_labels`
- `gljcvi-synteny` 不再提供 workflow 选择器和 histogram 参数；它通过 `target_gene_ids` 自动在 `graphics_synteny` 与 `local_synteny` 之间路由。

### 4. 构建脚本

使用并维护 `scripts/build_gljcvi_feature_plugin.ps1`：

```powershell
# 一站式工作流
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny

# lightweight 子模块插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature pairwise
scripts/build_gljcvi_feature_plugin.ps1 -Feature dotplot
scripts/build_gljcvi_feature_plugin.ps1 -Feature synteny_figure
scripts/build_gljcvi_feature_plugin.ps1 -Feature karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature local_synteny
scripts/build_gljcvi_feature_plugin.ps1 -Feature histogram
scripts/build_gljcvi_feature_plugin.ps1 -Feature heatmap

# aggregate 子模块插件
scripts/build_gljcvi_feature_plugin.ps1 -Feature global_karyotype
scripts/build_gljcvi_feature_plugin.ps1 -Feature multi_local_synteny
```

产物目录：

- `app/onestop/gljcvi-synteny.zip`
- `app/submodules/lightweight/gljcvi-<feature>.zip`（7 个）
- `app/submodules/aggregate/gljcvi-<feature>.zip`（2 个）

旧产物目录 `app/workflow-plugins/` 与 `app/gljcvi-auto/` 已废弃，应删除。旧入口 `mcscan_pairwise`、`catalog_ortholog` 与 `workflow_request v2` 独立可视化插件也不再构建。

### 5. 测试

`integrations/haiant_plugin/tests/`：

- `test_core.py`：测试 `_core.py` 的 `load_params`、`resolve_param_path`、`parse_bool`、`build_workflow_request`、`build_run_command`、`build_submodule_request`、`setup_adapter_logging`。
- `test_feature_entries.py`：验证每个 feature 入口生成正确的 `module_id` / `workflow_id` 与 `analyze run` 命令。

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
