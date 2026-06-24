"""Environment check contract models."""

from __future__ import annotations

from dataclasses import dataclass, field

from genomelens.utils.json import _dict_list, _str, _str_list


@dataclass(frozen=True)
class CheckToolItem:
    """CheckToolItem(检查工具项)：单个工具/引擎的诊断结果"""

    # fmt: off
    status: str        # 工具/引擎诊断状态（ok/missing/error/unknown）
    path: str = ""     # 可执行文件路径，缺失时为空
    message: str = ""  # 面向用户的诊断说明
    extra: dict[str, object] = field(default_factory=dict)  # 扩展字段（版本、候选名等）
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {"status": self.status}
        if self.path:
            data["path"] = self.path
        if self.message:
            data["message"] = self.message
        if self.extra:
            data.update(self.extra)
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> CheckToolItem:
        """从 JSON object(JSON 对象) 读取"""

        extra = {k: v for k, v in data.items() if k not in {"status", "path", "message"}}
        return cls(
            status=_str(data.get("status")),
            path=_str(data.get("path")),
            message=_str(data.get("message")),
            extra=extra,
        )


@dataclass(frozen=True)
class CheckReport:
    """CheckReport(检查报告)：check 命令的结构化输出"""

    # fmt: off
    status: str                 # 整体环境检查结果（ok/partial/failed）
    blastn: CheckToolItem       # BLAST+ blastn 诊断结果
    makeblastdb: CheckToolItem  # BLAST+ makeblastdb 诊断结果
    magick: CheckToolItem       # ImageMagick 诊断结果
    jcvi_engine: CheckToolItem  # jcvi-genomelens 引擎诊断结果
    install_attempts: list[dict[str, object]] = field(default_factory=list)  # 自动安装尝试记录
    engine_candidate_names: list[str] = field(default_factory=list)          # 引擎可执行文件名候选列表
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "status": self.status,
            "blastn": self.blastn.to_json(),
            "makeblastdb": self.makeblastdb.to_json(),
            "magick": self.magick.to_json(),
            "jcvi_engine": self.jcvi_engine.to_json(),
            "install_attempts": list(self.install_attempts),
            "engine_candidate_names": list(self.engine_candidate_names),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> CheckReport:
        """从 JSON object(JSON 对象) 读取"""

        def _tool(key: str) -> CheckToolItem:
            item = data.get(key)
            return CheckToolItem.from_json(item) if isinstance(item, dict) else CheckToolItem(status="unknown")

        return cls(
            status=_str(data.get("status")),
            blastn=_tool("blastn"),
            makeblastdb=_tool("makeblastdb"),
            magick=_tool("magick"),
            jcvi_engine=_tool("jcvi_engine"),
            install_attempts=_dict_list(data.get("install_attempts")),
            engine_candidate_names=_str_list(data.get("engine_candidate_names")),
        )
