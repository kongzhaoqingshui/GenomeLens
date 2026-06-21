# gljcvimcscan Action Notes

- 日期: 2026-06-21
- 主题: HAIant 共享核心与重型中心入口实现决策

## 决策

1. `genomelens_haiant_plugin` 改为包目录，新增 `_core.py` 承载共享逻辑。
   兼容脚本 `src/genomelens_haiant_plugin.py` 保留为可执行 shim，仅转调包内 `main()`。
2. `target_gene_ids` 同时兼容两种输入形态：
   - 逗号分隔字符串
   - JSON list
   另保留 `target_genes` 作为别名，便于与 CLI 文档表述对齐。
3. `discover_mcscan_home()` 的发现顺序固定为：
   - `GLJCVIMCSCAN_HOME`
   - 从当前插件目录向上搜索名为 `gljcvimcscan` 且包含 `genomelens` 壳的目录
4. `gljcvimcscan_entry.py` 固定写出 `workflow="local_synteny"` 的 `genomelens_request.json`，
   然后调用同目录平台级 `genomelens` 壳，而不是直接拼接或重实现 CLI。

## 原因

- 包结构能让轻型旧入口和未来子插件共享同一套请求组装、日志和发现逻辑。
- `target_gene_ids` 的双格式兼容更适合 HAIant 表单与手工 JSON 两种来源。
- 发现逻辑与 `ARCHITECTURE.md` 一致，且便于测试。
