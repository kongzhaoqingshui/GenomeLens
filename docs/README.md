# GenomeLens 文档

本目录只保留当前运行、交付、插件集成和源码维护需要的文档。

如果你现在只是想跑通 GenomeLens，优先看下面这几份：

- `../README.md`：项目概览、当前能力和开发入口。
- `使用方法/README.md`：从输入目录到结果目录的实际使用方式。
- `CLI.md`：当前 CLI 命令树、帮助入口和参数页。
- `使用方法/配置文件说明.md`：`genomelens.config.json` 与 `jcvi.config.json`。
- `TOOLCHAINS.md`：BLAST+、jcvi-genomelens、ImageMagick 的定位与缓存规则。

## 当前用户文档

- `项目介绍.md`：项目目标、当前边界和模块职责。
- `使用方法/README.md`：推荐使用路径与常见命令示例。
- `使用方法/配置文件说明.md`：配置字段、优先级和示例。
- `使用方法/JCVI能力与配置.md`：workflow、局部共线性链路和配置重点。
- `CLI.md`：CLI 契约和帮助页入口。
- `TOOLCHAINS.md`：运行时工具链说明。
- `DELIVERY.md`：交付包与发布说明。

## 当前开发文档

- `开发手册/README.md`：开发环境、测试与构建入口。
- `开发手册/代码风格规范.md`：代码风格和 `ruff` 规则。
- `开发手册/能力接入规则.md`：新增能力时要同步的协议、测试和文档。
- `开发手册/协作开发方案.md`：分支、评审与协作约定。

## 维护原则

删除未实现路线图和重复索引类说明后，当前行为以代码、`CLI.md`、`使用方法/README.md`、`DELIVERY.md` 和根 `README.md` 为准。
