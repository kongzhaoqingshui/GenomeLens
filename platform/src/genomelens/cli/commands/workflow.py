"""`genomelens workflow` metadata command."""

from __future__ import annotations

import argparse
import json
from typing import Any, cast

from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.loader import load_analysis_request
from genomelens.analysis.workflows.input_bindings import PortSystem
from genomelens.analysis.workflows.onestop import OneStopWorkflowSpec, get_onestop_registry
from genomelens.analysis.workflows.registry import list_one_stop_workflows
from genomelens.analysis.workflows.submodules import SubModuleKind, SubModuleSpec, get_submodule_registry
from genomelens.cli.ui import ConsoleWriter, StyledArgumentParser

_CONSOLE = ConsoleWriter()


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("workflow", help="列出、描述与验证工作流元数据")
    nested = parser.add_subparsers(dest="workflow_command", required=True, parser_class=StyledArgumentParser)

    list_parser = nested.add_parser("list", help="列出一站式工作流或子模块")
    list_parser.add_argument(
        "--kind", choices=["one_stop", "sub_module", "all"], default="all", help="要列出的能力类型"
    )
    list_parser.add_argument(
        "--module-kind",
        choices=["lightweight", "aggregate", "all"],
        default="all",
        help="按子模块编排类型筛选",
    )
    list_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    list_parser.set_defaults(func=_list)

    describe_parser = nested.add_parser("describe", help="描述工作流或子模块")
    describe_parser.add_argument("id", help="workflow_id 或 module_id")
    describe_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    describe_parser.set_defaults(func=_describe)

    validate_parser = nested.add_parser("validate", help="验证端口或 WorkflowRequest")
    validate_parser.add_argument("--submodule", default="", help="子模块 module_id")
    validate_parser.add_argument("--ports", default="", help="端口绑定 JSON 对象")
    validate_parser.add_argument("--request", default="", help="WorkflowRequest JSON 路径")
    validate_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读 JSON")
    validate_parser.set_defaults(func=_validate)


def _find_spec(spec_id: str) -> OneStopWorkflowSpec | SubModuleSpec | None:
    onestop = get_onestop_registry().get(spec_id)
    if onestop is not None:
        return onestop
    return get_submodule_registry().get(spec_id)


def _spec_kind(spec: OneStopWorkflowSpec | SubModuleSpec) -> str:
    return "one_stop" if isinstance(spec, OneStopWorkflowSpec) else "sub_module"


def _list(args: argparse.Namespace) -> int:
    kind: str = args.kind
    module_kind: str = args.module_kind
    include_one_stop = kind in {"one_stop", "all"}
    include_sub_module = kind in {"sub_module", "all"}
    one_stop = [spec.to_json() for spec in list_one_stop_workflows()] if include_one_stop else []
    if include_sub_module:
        submodule_specs = (
            get_submodule_registry().list_all()
            if module_kind == "all"
            else get_submodule_registry().list_by_kind(cast(SubModuleKind, module_kind))
        )
        sub_modules = [spec.to_json() for spec in submodule_specs]
    else:
        sub_modules = []

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
        lines.append("One-Stop Workflows")
        lines.append("-" * 40)
        lines.extend(f"  {item['workflow_id']:<30} {item['name']}" for item in one_stop)
        if include_sub_module:
            lines.append("")
    if include_sub_module:
        lines.append("Submodules")
        lines.append("-" * 40)
        lines.extend(f"  [{item['module_kind']:<11}] {item['module_id']:<40} {item['name']}" for item in sub_modules)
    _CONSOLE.print_text("\n".join(lines))
    return 0


def _describe(args: argparse.Namespace) -> int:
    spec = _find_spec(args.id)
    if spec is None:
        _CONSOLE.print_error(f"Workflow or submodule not found: {args.id}")
        return 2

    if args.json:
        payload = spec.to_json()
        payload["kind"] = _spec_kind(spec)
        _CONSOLE.print_json(payload)
        return 0

    payload = spec.to_json()
    lines = [f"ID:   {payload.get('workflow_id') or payload.get('module_id')}", f"Kind: {_spec_kind(spec)}"]
    for key in ("name", "category", "module_kind", "engine_workflow", "runner"):
        if key in payload:
            lines.append(f"{key}: {payload[key]}")
    _CONSOLE.print_text("\n".join(lines))
    return 0


def _load_json(value: str) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("JSON value must be an object")
    return parsed


def _validate(args: argparse.Namespace) -> int:
    errors: list[str] = []

    if args.request:
        try:
            WorkflowPlanner().build(load_analysis_request(args.request))
        except Exception as exc:  # noqa: BLE001 - validation command reports all errors as text
            errors.append(str(exc))

    if args.submodule:
        spec = get_submodule_registry().get(args.submodule)
        if spec is None:
            errors.append(f"Unknown submodule: {args.submodule}")
        else:
            errors.extend(PortSystem.validate_bindings(spec.inputs, _load_json(args.ports)))

    if not args.request and not args.submodule:
        errors.append("Provide --request or --submodule")

    if args.json:
        _CONSOLE.print_json({"valid": not errors, "errors": errors})
    elif errors:
        _CONSOLE.print_error("Validation failed:\n" + "\n".join(f"  - {item}" for item in errors))
    else:
        _CONSOLE.print_text("Validation passed")
    return 0 if not errors else 3
