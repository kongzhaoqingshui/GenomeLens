"""端口系统：为可编排子模块提供显式输入/输出声明与绑定验证"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# endregion


@dataclass(frozen=True)
class PortDeclaration:
    """端口声明：描述子模块的某个输入或输出端口"""

    port_id: str
    port_kind: Literal["species_pair", "species_list", "artifact", "value", "config"]
    required: bool
    description: str
    artifact_type: str | None = None
    accepted_formats: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "port_id": self.port_id,
            "port_kind": self.port_kind,
            "required": self.required,
            "description": self.description,
        }
        if self.artifact_type:
            data["artifact_type"] = self.artifact_type
        if self.accepted_formats:
            data["accepted_formats"] = list(self.accepted_formats)
        return data


@dataclass(frozen=True)
class PortBinding:
    """端口绑定：运行时某个端口的具体值"""

    port_id: str
    value: object

    def to_json(self) -> dict[str, object]:
        return {"port_id": self.port_id, "value": self.value}


class PortSystem:
    """端口系统：提供端口绑定验证与兼容性检查"""

    @staticmethod
    def validate_bindings(
        inputs: list[PortDeclaration],
        port_bindings: dict[str, object],
    ) -> list[str]:
        """验证端口绑定是否满足输入声明，返回错误信息列表（空表示通过）"""

        errors: list[str] = []
        required_ids = {p.port_id for p in inputs if p.required}
        provided_ids = set(port_bindings.keys())
        known_ids = {p.port_id for p in inputs}

        missing = required_ids - provided_ids
        if missing:
            errors.append(f"缺少必填端口：{sorted(missing)}")

        unknown = provided_ids - known_ids
        if unknown:
            errors.append(f"存在未知端口：{sorted(unknown)}")

        return errors

    @staticmethod
    def describe_ports(ports: list[PortDeclaration]) -> list[dict[str, object]]:
        """把端口声明列表转为可序列化描述"""

        return [port.to_json() for port in ports]
