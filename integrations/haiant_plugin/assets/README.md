# HAIant assets（智然体资源）

- `config.json`：智然体平台表单 metadata（元数据），包含 2 到 n 个物种的 `species[]` 参数和一站式 JCVI 出图入口。
- `params.json`：可运行的双物种示例参数文件；需要多物种时继续向 `species[]` 追加条目。
- `README.md`：供插件包维护者查看的资源说明。

插件不会直接拼接旧版 `analyze mcscan` 手动参数。插件会先写出 `genomelens_request.json`，再调用 `analyze run <request.json>`。

## 新架构说明

本项目正在迁移到**一重型中心 + 多轻量子插件**模型，详见 `../ARCHITECTURE.md`：

- 重型中心 `gljcvimcscan`：携带完整 GL platform 与工具链，提供 `genomelens` 命令壳。
- 轻量子插件：每个 JCVI 小功能一个独立包，通过 `GLJCVIMCSCAN_HOME` 或父目录搜索定位重型中心。

本目录下的 `config.json` / `params.json` 是旧单包插件（兼容入口）的默认配置。新模型下每个 workflow 会有独立的 `assets/<feature>/config.json`。
