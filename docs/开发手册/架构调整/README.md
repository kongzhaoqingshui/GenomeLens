# 架构调整文档

本目录只保留当前架构判断和仍会指导后续开发的文档。早期的一站式 workflow 草案、端口草案、注册表草案已经归档到 `docs/历史/开发手册/`。

## 当前文档

| 文档 | 内容 |
|---|---|
| [最终架构目标](最终架构目标.md) | GenomeLens 长期平台架构、分层边界和 V2 协议定位 |
| [多平台兼容方案](多平台兼容方案.md) | Windows-first 到多平台运行时的演进策略 |
| [Platform + JCVI Engine 分包重构 V2](platform-engine-package-refactor-v2.md) | 当前 platform 与 JCVI engine 分包结果 |
| [工作流与注册表当前结构](工作流与注册表.md) | workflow registry、submodule、port binding、planner/executor 的当前代码位置 |

## 阅读顺序

1. 先读 [最终架构目标](最终架构目标.md)，理解平台边界。
2. 再读 [Platform + JCVI Engine 分包重构 V2](platform-engine-package-refactor-v2.md)，理解当前代码结构。
3. 需要新增能力时，读 [工作流与注册表当前结构](工作流与注册表.md) 和 [能力接入规则](../能力接入规则.md)。
