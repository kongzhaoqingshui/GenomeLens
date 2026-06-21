# HAIant 插件架构重构计划

- **日期**: 2026-06-21
- **版本**: 归属 v0.9.x / 未来 v1.0.0 插件体系
- **复杂度**: 高
- **涉及模块**:
  - `integrations/haiant_plugin/`（源码、配置、文档、测试）
  - `scripts/`（构建脚本）
  - `docs/开发手册/`（架构说明）
- **验收标准**:
  - [ ] 完成一重型中心 `gljcvimcscan` + 多轻量子插件的架构文档
  - [ ] 更新现有 `PARAMETER_MAPPING.md` 与 `assets/README.md`
  - [ ] 给出可直接交给子 Agent 的初始提示词
  - [ ] 不破坏现有 `genomelens_haiant_plugin.py` 的公开行为
- **技术债务**: 当前插件是单体式大包围，未来需要拆成多包；本次只做设计与文档，代码实现由子 Agent 按提示词完成。

## 设计要点

1. **GL 入口加壳**：新增 `genomelens` 命令作为环境变量壳，设置 `GENOMELENS_HOME` / `GENOMELENS_TOOLCHAIN_DIR` 后调用 `GenomeLens-runtime.exe`。
2. **重型中心 `gljcvimcscan`**：一个独立的 HAIant 插件包，携带完整 GL platform、BLAST/JCVI/ImageMagick 工具链，自身负责 JCVI 局部共线性分析工作流。
3. **轻量子插件**：每个 JCVI 小功能一个插件包，只带入口、`config.json`、`params.json`、`README.md`。入口通过 `GLJCVIMCSCAN_HOME` 环境变量或向上搜索 `gljcvimcscan/` 目录来定位重型中心，再调用其 `genomelens analyze run <request.json>`。
4. **兼容 HAIant 约束**：入口必须接收 `params.json` 路径、输出 `run.log`、捕获异常、支持 PyInstaller 打包。

## 关联文档

- `integrations/haiant_plugin/ARCHITECTURE.md`（新建）
- `integrations/haiant_plugin/PARAMETER_MAPPING.md`（更新）
- `integrations/haiant_plugin/assets/README.md`（更新）
- `docs/开发手册/子Agent提示词-智然体插件搭建.md`（新建）
