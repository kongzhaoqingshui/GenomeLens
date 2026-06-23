"""GenomeLens 工作流编排元数据层

本层负责维护可编排子模块（Composable Sub-Module）与一站式工作流（One-Stop
Workflow）的元数据、输入/输出端口声明与能力发现接口。

设计目标：
- 为每个子模块定义显式输入/输出端口，支撑未来 GUI 的积木式可视化编排。
- 为一站式工作流保留独立、可优化的执行路径，区别于子模块的简单拼接。
- 提供平台级能力发现（list/describe），供 CLI、GUI、插件统一消费。
"""

# region import
from __future__ import annotations

from genomelens.workflow.onestop_registry import OneStopWorkflowRegistry, OneStopWorkflowSpec
from genomelens.workflow.port_system import PortDeclaration, PortSystem
from genomelens.workflow.submodule_registry import SubModuleRegistry, SubModuleSpec

# endregion


__all__ = [
    "PortDeclaration",
    "PortSystem",
    "SubModuleRegistry",
    "SubModuleSpec",
    "OneStopWorkflowRegistry",
    "OneStopWorkflowSpec",
]
