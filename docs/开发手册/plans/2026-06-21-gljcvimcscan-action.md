# gljcvimcscan Action Notes

- 日期: 2026-06-21
- 主题: HAIant 共享核心与重型中心入口实现决策
- **状态：已废弃**

> 本文档记录的“一重型中心 + 多轻量子插件”模型已被移除。
> 当前 HAIant 插件体系为完全独立的轻量插件，每个插件直接通过 `genomelens_exe` / `GENOMELENS_EXE` 调用外部 GenomeLens，不再依赖 `gljcvimcscan` 重型中心或 `GLJCVIMCSCAN_HOME`。
> 保留本文档仅作历史参考。

## 历史决策

1. `genomelens_haiant_plugin` 改为包目录，新增 `_core.py` 承载共享逻辑。
2. `target_gene_ids` 同时兼容两种输入形态：
   - 逗号分隔字符串
   - JSON list
   另保留 `target_genes` 作为别名。
3. `discover_mcscan_home()` 的发现顺序固定为：
   - `GLJCVIMCSCAN_HOME`
   - 从当前插件目录向上搜索名为 `gljcvimcscan` 且包含 `genomelens` 壳的目录
4. `gljcvimcscan_entry.py` 固定写出 `workflow="local_synteny"` 的 `genomelens_request.json`，然后调用同目录平台级 `genomelens` 壳。

## 当前等价能力

- 共享核心 `_core.py` 继续保留，但已移除重型中心相关 helper（`discover_mcscan_home`、`genomelens_shell_path`、`GLJCVIMCSCAN_HOME` 等）。
- `local_synteny` 由独立插件 `gljcvi-local-synteny` 提供，行为与历史重型中心入口一致。
- `gljcvi-auto` 固定为 `workflow="graphics_synteny"` 一键自动流。
