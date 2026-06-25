"""TaskRequest 联合加载器：按 kind 自动分发 WorkflowRequest / SubmoduleRequest"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.requests.submodule_models import SubmoduleRequest
from genomelens.app.errors.exceptions import InputValidationError

# endregion


def load_task_request(path: str | Path) -> WorkflowRequest | SubmoduleRequest:
    """从 JSON 文件读取任务请求，按 kind 自动分发"""

    source = Path(path).expanduser().resolve(strict=False)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise InputValidationError(f"task request 必须是 JSON object(对象)：{source}")

    kind = data.get("kind")
    try:
        if kind == "workflow_request":
            request: WorkflowRequest | SubmoduleRequest = WorkflowRequest.from_json(data)
            if request.schema_version != 3:
                raise InputValidationError(f"不支持的 WorkflowRequest schema version：{request.schema_version}")
            return request
        if kind == "submodule_request":
            request = SubmoduleRequest.from_json(data)
            if request.schema_version != 3:
                raise InputValidationError(f"不支持的 SubmoduleRequest schema version：{request.schema_version}")
            return request
    except ValueError as exc:
        raise InputValidationError(str(exc)) from exc

    raise InputValidationError(f"不支持的 request kind(请求类型)：{kind!r}")


def write_task_request(request: WorkflowRequest | SubmoduleRequest, path: str | Path) -> Path:
    """写出任务请求 JSON"""

    target = Path(path).expanduser().resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(request.to_json(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


__all__ = ["load_task_request", "write_task_request"]
