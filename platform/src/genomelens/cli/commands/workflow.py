"""`genomelens workflow` 命令

列出、描述和验证可编排子模块与一站式工作流的元数据。
"""

# region import
from __future__ import annotations

import argparse
import json
from typing import Any

from genomelens.analysis.methods.registry import list_one_stop_workflows, list_submodules
from genomelens.analysis.requests.loader import load_analysis_request
from genomelens.cli.ui import ConsoleWriter
from genomelens.workflow.onestop_registry import OneStopWorkflowSpec, get_onestop_registry
from genomelens.workflow.port_system import PortSystem
from genomelens.workflow.submodule_registry import SubModuleSpec, get_submodule_registry

# endregion


_CONSOLE = ConsoleWriter()


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 workflow 命令"""

    parser = subparsers.add_parser("workflow", help="列出、描述和验证工作流/子模块")
    nested = parser.add_subparsers(dest="workflow_command", required=True)

    list_parser = nested.add_parser("list", help="列出可用的一站式工作流或可编排子模块")
    list_parser.add_argument(
        "--kind",
        choices=["one_stop", "sub_module", "all"],
        default="all",
        help="要列出的条目类型",
    )
    list_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    list_parser.set_defaults(func=_list)

    describe_parser = nested.add_parser("describe", help="描述指定的工作流或子模块")
    describe_parser.add_argument("id", help="workflow_id 或 module_id")
    describe_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    describe_parser.set_defaults(func=_describe)

    validate_parser = nested.add_parser("validate", help="验证端口绑定或 AnalysisRequest")
    validate_parser.add_argument("--submodule", default="", help="子模块 module_id")
    validate_parser.add_argument("--ports", default="", help='端口绑定 JSON，例如 {"species_pair": ["A", "B"]}')
    validate_parser.add_argument("--request", default="", help="AnalysisRequest JSON 文件路径")
    validate_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    validate_parser.set_defaults(func=_validate)


def _find_spec(spec_id: str) -> OneStopWorkflowSpec | SubModuleSpec | None:
    """按 ID 查找一站式工作流或子模块规范"""

    onestop = get_onestop_registry().get(spec_id)
    if onestop is not None:
        return onestop
    return get_submodule_registry().get(spec_id)


def _spec_kind(spec: OneStopWorkflowSpec | SubModuleSpec) -> str:
    """返回规范类型标识"""

    return "one_stop" if isinstance(spec, OneStopWorkflowSpec) else "sub_module"


def _list(args: argparse.Namespace) -> int:
    """列出工作流/子模块"""

    kind: str = args.kind
    include_one_stop = kind in {"one_stop", "all"}
    include_sub_module = kind in {"sub_module", "all"}

    one_stop = [spec.to_json() for spec in list_one_stop_workflows()] if include_one_stop else []
    sub_modules = [spec.to_json() for spec in list_submodules()] if include_sub_module else []

    if args.json:
        payload: dict[str, object] = {}
        if include_one_stop:
            payload["one_stop_workflows"] = one_stop
        if include_sub_module:
            payload["submodules"] = sub_modules
        _CONSOLE.print_json(payload)
        return 0

    lines: list[str] = []
    if include_one_stop:
        lines.append("一站式工作流 (One-Stop Workflows)")
        lines.append("-" * 40)
        for spec in one_stop:
            lines.append(f"  {spec['workflow_id']:<30} {spec['name']}")
        if include_sub_module:
            lines.append("")
    if include_sub_module:
        lines.append("可编排子模块 (Sub-Modules)")
        lines.append("-" * 40)
        for spec in sub_modules:
            lines.append(f"  {spec['module_id']:<40} {spec['name']}")
    _CONSOLE.print_text("\n".join(lines))
    return 0


def _describe(args: argparse.Namespace) -> int:
    """描述单个工作流/子模块"""

    spec = _find_spec(args.id)
    if spec is None:
        _CONSOLE.print_error(f"未找到工作流或子模块：{args.id}")
        return 2

    if args.json:
        payload = spec.to_json()
        payload["kind"] = _spec_kind(spec)
        _CONSOLE.print_json(payload)
        return 0

    lines: list[str] = []
    if isinstance(spec, OneStopWorkflowSpec):
        lines.append(f"ID:        {spec.workflow_id}")
        lines.append("类型:      一站式工作流")
        lines.append(f"名称:      {spec.name}")
        lines.append(f"分类:      {spec.category}")
        lines.append(f"Runner:    {spec.runner}")
        lines.append(f"Engine:    {spec.engine_workflow or '-'}")
        lines.append(f"等价子模块: {', '.join(spec.equivalent_modules)}")
        lines.append(f"优化说明:  {spec.optimization_notes}")
    else:
        lines.append(f"ID:        {spec.module_id}")
        lines.append("类型:      可编排子模块")
        lines.append(f"名称:      {spec.name}")
        lines.append(f"分类:      {spec.category}")
        lines.append(f"Engine:    {spec.engine_workflow}")
        lines.append(f"可独立运行: {spec.standalone}")
        lines.append("输入端口:")
        for port in PortSystem.describe_ports(spec.inputs):
            required = "必填" if port["required"] else "可选"
            lines.append(f"  - {port['port_id']} ({port['port_kind']}, {required}): {port['description']}")
        lines.append("输出端口:")
        for port in PortSystem.describe_ports(spec.outputs):
            lines.append(f"  - {port['port_id']} ({port['port_kind']}): {port['description']}")
        lines.append("参数:")
        for param in spec.parameters:
            lines.append(f"  - {param.param_id}: {param.description}")
    _CONSOLE.print_text("\n".join(lines))
    return 0


def _load_json(value: str) -> dict[str, Any]:
    """安全解析 JSON 字符串，失败时抛出可读错误"""

    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"无法解析 JSON：{exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("JSON 必须是一个对象")
    return parsed


def _validate(args: argparse.Namespace) -> int:
    """验证端口绑定或 AnalysisRequest"""

    errors: list[str] = []

    if args.request:
        try:
            request = load_analysis_request(args.request)
            if request.task_kind == "one_stop" and not request.one_stop_workflow_id:
                errors.append("task_kind=one_stop 时必须提供 one_stop_workflow_id")
            if request.task_kind == "sub_module":
                if not request.sub_module_id:
                    errors.append("task_kind=sub_module 时必须提供 sub_module_id")
                else:
                    spec = get_submodule_registry().get(request.sub_module_id)
                    if spec is None:
                        errors.append(f"未知子模块：{request.sub_module_id}")
                    else:
                        errors.extend(PortSystem.validate_bindings(spec.inputs, request.port_bindings))
            if request.task_kind == "composition" and not request.composition:
                errors.append("task_kind=composition 时必须提供 composition")
        except Exception as exc:  # noqa: BLE001 - 验证命令需要把错误写入报告
            errors.append(str(exc))

    if args.submodule:
        spec = get_submodule_registry().get(args.submodule)
        if spec is None:
            errors.append(f"未知子模块：{args.submodule}")
        else:
            ports = _load_json(args.ports)
            errors.extend(PortSystem.validate_bindings(spec.inputs, ports))

    if not args.request and not args.submodule:
        errors.append("请提供 --request 或 --submodule 进行验证")

    if args.json:
        _CONSOLE.print_json({"valid": not errors, "errors": errors})
    elif errors:
        _CONSOLE.print_error("验证失败：\n" + "\n".join(f"  - {e}" for e in errors))
    else:
        _CONSOLE.print_text("验证通过")

    return 0 if not errors else 3
