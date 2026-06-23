"""Sub-module runner：独立执行单个可编排子模块"""

# region import
from __future__ import annotations

from dataclasses import replace

from genomelens.analysis.methods.mcscan_request_mapping import (
    to_heatmap_request,
    to_histogram_request,
    to_mcscan_request,
)
from genomelens.analysis.requests.models import AnalysisInput, AnalysisRequest
from genomelens.app.controller.runners.heatmap_runner import run_heatmap_workflow
from genomelens.app.controller.runners.histogram_runner import run_histogram_workflow
from genomelens.app.controller.runners.pairwise_runner import run_pairwise_mcscan
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary
from genomelens.workflow.port_system import PortSystem
from genomelens.workflow.submodule_registry import get_submodule_registry

# endregion


class SubModuleRunner:
    """SubModuleRunner：按 sub_module_id 查找规范、校验端口并执行子模块

    当前优先支持可独立运行、输入简单的子模块；依赖前置产物的可视化子模块
    将在引擎层进一步拆分后逐步接入。
    """

    def run(
        self,
        request: AnalysisRequest,
        _provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """执行子模块请求"""

        module_id = request.sub_module_id
        if not module_id:
            raise InputValidationError("task_kind=sub_module 时必须提供 sub_module_id")

        registry = get_submodule_registry()
        spec = registry.get(module_id)
        if spec is None:
            raise InputValidationError(f"未知的子模块：{module_id}")

        errors = PortSystem.validate_bindings(spec.inputs, request.port_bindings)
        if errors:
            raise InputValidationError("; ".join(errors))

        delegate = self._build_delegate(request, spec)

        def _set_state(state: WorkflowState) -> None:
            signal_bus.emit("state", state=state.value)

        if spec.engine_workflow == "graphics_histogram":
            summary = run_histogram_workflow(_set_state, to_histogram_request(delegate))
        elif spec.engine_workflow == "graphics_heatmap":
            summary = run_heatmap_workflow(_set_state, to_heatmap_request(delegate))
        elif spec.engine_workflow == "mcscan_pairwise":
            summary = run_pairwise_mcscan(_set_state, to_mcscan_request(delegate))
        else:
            raise InputValidationError(
                f"子模块 {module_id} 的独立执行路径尚未实现；"
                "当前仅支持 jcvi.mcscan_pairwise、jcvi.graphics_histogram 与 jcvi.graphics_heatmap"
            )

        return replace(summary, task={**summary.task, "sub_module_id": module_id})

    def _build_delegate(self, request: AnalysisRequest, spec) -> AnalysisRequest:
        """把子模块端口绑定转成现有 runner 能消费的 AnalysisRequest"""

        bindings = request.port_bindings
        method_config = dict(request.method_config)
        method_config["workflow"] = spec.engine_workflow

        if spec.engine_workflow == "graphics_histogram":
            raw_numeric = bindings.get("numeric_files")
            numeric_files = list(raw_numeric) if isinstance(raw_numeric, list) else []
            if not numeric_files:
                raise InputValidationError("graphics_histogram 子模块缺少 numeric_files 端口绑定")
            method_config["histogram_inputs"] = numeric_files
            method_config.setdefault("histogram_columns", [0])
            return replace(
                request,
                input=AnalysisInput(
                    mode="method_specific",
                    directory=str(numeric_files[0]),
                    species=[],
                    reference_index=0,
                ),
                method_config=method_config,
                task_kind="analysis",
                sub_module_id=None,
                port_bindings={},
            )

        if spec.engine_workflow == "graphics_heatmap":
            matrix = bindings.get("matrix_csv")
            if not isinstance(matrix, str) or not matrix:
                raise InputValidationError("graphics_heatmap 子模块缺少 matrix_csv 端口绑定")
            method_config["matrix"] = matrix
            return replace(
                request,
                input=AnalysisInput(
                    mode="method_specific",
                    directory=str(matrix),
                    species=[],
                    reference_index=0,
                ),
                method_config=method_config,
                task_kind="analysis",
                sub_module_id=None,
                port_bindings={},
            )

        if spec.engine_workflow == "mcscan_pairwise":
            species_pair = bindings.get("species_pair")
            if isinstance(species_pair, list) and len(species_pair) == 2:
                # 若端口绑定的是物种名称列表，默认使用 auto_directory 发现文件
                input_dir = str(request.input.directory) if request.input.directory else ""
            elif isinstance(species_pair, str):
                input_dir = species_pair
            else:
                raise InputValidationError("mcscan_pairwise 子模块的 species_pair 端口应为目录路径或两个物种名")
            return replace(
                request,
                input=AnalysisInput(
                    mode="auto_directory",
                    directory=input_dir,
                    species=list(request.input.species),
                    reference_index=request.input.reference_index,
                ),
                method_config=method_config,
                task_kind="analysis",
                sub_module_id=None,
                port_bindings={},
            )

        raise InputValidationError(f"子模块 {spec.module_id} 的端口映射尚未实现")
