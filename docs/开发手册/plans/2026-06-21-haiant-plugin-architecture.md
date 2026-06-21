# HAIant 插件架构重构计划

- **日期**: 2026-06-21
- **版本**: 归属 v0.9.18 / 未来 v1.0.0 插件体系
- **复杂度**: 高
- **涉及模块**:
  - `integrations/haiant_plugin/`（源码、配置、文档、测试）
  - `scripts/`（构建脚本）
  - `docs/开发手册/`（架构说明）
- **验收标准**:
  - [x] 完成完全独立的轻量插件架构
  - [x] 每个 JCVI 小功能一个独立插件包
  - [x] `gljcvi-auto` 固定对应 `analyze mcscan jcvi` 一键自动流
  - [x] 更新 `PARAMETER_MAPPING.md`、`ARCHITECTURE.md`、`assets/README.md`
  - [x] 移除旧单包插件、重型中心 `gljcvimcscan` 及相关构建脚本
  - [x] 不破坏现有 `features/*_entry.py` 与 `_core.py` 的公开行为

## 最终设计要点

1. **外部 GenomeLens 可执行文件**：所有插件通过 `genomelens_exe` 参数或 `GENOMELENS_EXE` 环境变量定位外部 GenomeLens；插件本身不携带平台或工具链。
2. **独立轻量插件**：每个 JCVI 小功能一个插件包：
   - `gljcvi-dotplot` — `graphics_dotplot`
   - `gljcvi-synteny` — `graphics_synteny`
   - `gljcvi-karyotype` — `graphics_karyotype`
   - `gljcvi-catalog-ortholog` — `catalog_ortholog`
   - `gljcvi-local-synteny` — `local_synteny`
3. **统一自动流插件**：`gljcvi-auto` 固定生成 `workflow = graphics_synteny` 的 AnalysisRequest；填写 `target_gene_ids` 时自动切换到局部共线性模式。
4. **移除旧模型**：
   - 删除 `src/gljcvimcscan_entry.py`、`src/genomelens_haiant_plugin/legacy_entry.py`
   - 删除 `assets/gljcvimcscan/`、`assets/config.json`、`assets/params.json`、`assets/README.md`
   - 删除 `pyinstaller/genomelens_haiant.spec`
   - 删除 `scripts/build_haiant_plugin.ps1`、`scripts/build_gljcvimcscan_center.ps1`
   - 从 `_core.py` 移除重型中心 helper 与旧单包入口
5. **兼容 HAIant 约束**：入口必须接收 `params.json` 路径、输出 `run.log`、捕获异常、支持 PyInstaller 打包。

## 关联文档

- `integrations/haiant_plugin/ARCHITECTURE.md`
- `integrations/haiant_plugin/PARAMETER_MAPPING.md`
- `integrations/haiant_plugin/README.md`
- `docs/开发手册/CLI入口壳设计.md`
