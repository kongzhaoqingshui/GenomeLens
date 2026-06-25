"""SubmoduleRequest 数据模型：原子子模块的公开请求协议"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from genomelens.analysis.requests.models import WorkflowOutput, WorkflowRuntime
from genomelens.utils.json import _dict, _int, _nested, _str

# endregion


@dataclass(frozen=True)
class SubmoduleRequest:
    """SubmoduleRequest(子模块请求)：可编排子模块的唯一标准请求"""

    # fmt: off
    module_id: str                                    # 子模块 ID，例如 jcvi.graphics_histogram
    inputs: dict[str, object] = field(default_factory=dict)   # 端口绑定，例如 {"numeric_files": [...]}
    parameters: dict[str, object] = field(default_factory=dict)  # 模块特定参数
    output: WorkflowOutput = field(default_factory=lambda: WorkflowOutput(directory=""))
    runtime: WorkflowRuntime = field(default_factory=WorkflowRuntime)
    schema_version: int = 3
    kind: str = "submodule_request"
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object"""

        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "module_id": self.module_id,
            "inputs": dict(self.inputs),
            "parameters": dict(self.parameters),
            "output": self.output.to_json(),
            "runtime": self.runtime.to_json(),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object 读取"""

        allowed = {
            "schema_version",
            "kind",
            "module_id",
            "inputs",
            "parameters",
            "output",
            "runtime",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"SubmoduleRequest contains unsupported fields: {', '.join(unknown)}")

        return cls(
            schema_version=_int(data.get("schema_version"), default=3),
            kind=_str(data.get("kind"), default="submodule_request"),
            module_id=_str(data.get("module_id")),
            inputs=_dict(data.get("inputs")),
            parameters=_dict(data.get("parameters")),
            output=_nested(WorkflowOutput, data.get("output")),
            runtime=_nested(WorkflowRuntime, data.get("runtime")),
        )


def submodule_template_request(module_id: str = "jcvi.graphics_histogram") -> SubmoduleRequest:
    """生成 SubmoduleRequest 模板"""

    inputs: dict[str, object]
    parameters: dict[str, object]
    if module_id == "jcvi.graphics_histogram":
        inputs = {"numeric_files": ["workspace/values.txt"]}
        parameters = {"columns": [0], "bins": 20}
    elif module_id == "jcvi.graphics_heatmap":
        inputs = {"matrix_csv": "workspace/matrix.csv"}
        parameters = {"cmap": "viridis"}
    else:
        inputs = {}
        parameters = {}

    return SubmoduleRequest(
        module_id=module_id,
        inputs=inputs,
        parameters=parameters,
        output=WorkflowOutput(directory="workspace/output", formats=["svg"]),
    )


__all__ = ["SubmoduleRequest", "submodule_template_request"]
