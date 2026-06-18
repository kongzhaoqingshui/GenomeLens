# HAIant assets(智然体资源)

- `config.json`：智然体平台表单 metadata(元数据)，包含 2 到 n 个物种的 `species[]` 参数和一站式 JCVI 出图入口。
- `params.json`：可运行的双物种示例参数文件；需要多物种时继续向 `species[]` 追加条目。
- `README.md`：供插件包维护者查看的资源说明。

插件不会直接拼接旧版 `analyze mcscan` 手动参数。插件会先写出 `genomelens_request.json`，再调用 `analyze run <request.json>`。
