"""读取、写入 workflow request(工作流请求)"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.app.errors.exceptions import InputValidationError

# endregion


def load_analysis_request(path: str | Path) -> WorkflowRequest:
    """从 JSON 文件读取 WorkflowRequest(工作流请求)"""

    source = Path(path).expanduser().resolve(strict=False)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise InputValidationError(f"workflow request 必须是 JSON object(对象)：{source}")

    try:
        request = WorkflowRequest.from_json(data)
    except ValueError as exc:
        raise InputValidationError(str(exc)) from exc
    if request.kind != "workflow_request":
        raise InputValidationError(f"不支持的 request kind(请求类型)：{request.kind}")
    if request.schema_version != 2:
        raise InputValidationError(f"不支持的 workflow request schema version：{request.schema_version}")
    return request


def write_analysis_request(request: WorkflowRequest, path: str | Path) -> Path:
    """写出 WorkflowRequest(工作流请求)"""

    target = Path(path).expanduser().resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(request.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
