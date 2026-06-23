"""Analysis method registry(分析方法注册表)

支持显式注册内置方法与 importlib.metadata.entry_points 动态加载第三方方法。
"""

# region import
from __future__ import annotations

import argparse
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.core.summary_models import RunSummary

# endregion


if TYPE_CHECKING:
    from genomelens.workflow.onestop_registry import OneStopWorkflowSpec
    from genomelens.workflow.submodule_registry import SubModuleSpec


@dataclass(frozen=True)
class ArtifactDeclaration:
    """ArtifactDeclaration(产物声明)：方法对外暴露的可生成产物元数据"""

    artifact_id: str
    artifact_type: str
    description: str = ""
    required: bool = False


@runtime_checkable
class MethodPlugin(Protocol):
    """MethodPlugin(方法插件)：接入 GenomeLens 平台的方法必须实现的协议"""

    @property
    def name(self) -> str:
        """返回方法唯一标识名"""

        ...

    @property
    def description(self) -> str:
        """返回供 CLI/GUI 展示的一行描述"""

        ...

    @property
    def stable(self) -> bool:
        """返回方法是否为稳定方法；False 时会在 UI 中标记为预览"""

        ...

    def validate_request(self, request: AnalysisRequest) -> None:
        """校验请求是否满足该方法的要求；不满足时应抛出 InputValidationError"""

        ...

    def get_provider(self) -> WorkflowProvider:
        """返回该方法对应的工作流提供者"""

        ...

    def add_cli_arguments(self, parser: argparse.ArgumentParser) -> None:
        """为 CLI 子命令注册该方法专属参数"""

        ...

    def build_request(self, args: argparse.Namespace) -> AnalysisRequest:
        """把解析后的 CLI 参数转成 AnalysisRequest"""

        ...

    def list_artifacts(self) -> list[ArtifactDeclaration]:
        """返回该方法可能产出的产物声明列表"""

        ...


MethodRunner = Callable[[AnalysisRequest], RunSummary]


def _call_optional(plugin: MethodPlugin, name: str) -> object:
    """安全调用插件的可选方法，不存在时返回默认值"""

    method = getattr(plugin, name, None)
    if callable(method):
        return method()
    return None


class MethodRegistry:
    """MethodRegistry(方法注册表)：管理所有可用的分析方法的注册与发现"""

    def __init__(self) -> None:
        self._plugins: dict[str, MethodPlugin] = {}
        self._register_builtins()
        self._load_entry_points()

    def _register_builtins(self) -> None:
        """注册平台内置方法"""

        from genomelens.analysis.methods.mcscan_plugin import McscanPlugin

        self.register(McscanPlugin())

    def _load_entry_points(self) -> None:
        """从 importlib.metadata entry_points 加载第三方方法插件

        每个 entry point 单独 try/except，加载失败仅发出 warning 不阻断平台启动。
        """

        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover - Python <3.10 回退
            return

        try:
            eps = entry_points(group="genomelens.methods")
        except Exception as exc:  # noqa: BLE001 - entry_points 失败不应影响内置方法
            warnings.warn(f"Failed to load genomelens.methods entry points: {exc}", stacklevel=2)
            return

        for ep in eps:
            try:
                plugin_factory = ep.load()
                plugin = plugin_factory()
                if not isinstance(plugin, MethodPlugin):
                    warnings.warn(
                        f"Entry point {ep.name!r} did not return a MethodPlugin instance; skipped",
                        stacklevel=2,
                    )
                    continue
                self.register(plugin)
            except Exception as exc:  # noqa: BLE001 - 单个插件失败不应影响其他插件
                warnings.warn(f"Failed to load method plugin {ep.name!r}: {exc}", stacklevel=2)

    def register(self, plugin: MethodPlugin) -> None:
        """显式注册一个方法插件"""

        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> MethodPlugin | None:
        """按名称返回已注册的方法插件"""

        return self._plugins.get(name)

    def list_all(self) -> list[MethodPlugin]:
        """按注册顺序返回全部方法插件"""

        return list(self._plugins.values())

    def list_submodules(self) -> list[SubModuleSpec]:
        """收集所有方法插件暴露的可编排子模块"""

        result: list[SubModuleSpec] = []
        for plugin in self._plugins.values():
            specs = _call_optional(plugin, "list_submodules")
            if isinstance(specs, list):
                result.extend(specs)
        return result

    def list_one_stop_workflows(self) -> list[OneStopWorkflowSpec]:
        """收集所有方法插件暴露的一站式工作流"""

        result: list[OneStopWorkflowSpec] = []
        for plugin in self._plugins.values():
            specs = _call_optional(plugin, "list_one_stop_workflows")
            if isinstance(specs, list):
                result.extend(specs)
        return result


# 模块级便捷函数，保持 cli/ui.py 等现有调用方不变
_registry = MethodRegistry()


def get_method(name: str) -> MethodPlugin | None:
    """返回指定 method(方法) 的插件"""

    return _registry.get(name)


def list_methods() -> list[MethodPlugin]:
    """按注册顺序返回全部 method(方法)"""

    return _registry.list_all()


def list_submodules() -> list[SubModuleSpec]:
    """返回所有方法插件暴露的可编排子模块"""

    return _registry.list_submodules()


def list_one_stop_workflows() -> list[OneStopWorkflowSpec]:
    """返回所有方法插件暴露的一站式工作流"""

    return _registry.list_one_stop_workflows()
