"""HAIant 插件入口的共享辅助函数"""

# region import
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Mapping, Sequence


LOGGER_NAME = "genomelens_haiant_plugin"
GENOMELENS_EXE_ENV = "GENOMELENS_EXE"

# endregion


class PluginError(Exception):
    """当 HAIant 入口无法构建有效的 GenomeLens 请求时抛出"""


def resource_path(*parts: str | Path) -> Path:
    """返回插件根目录下的路径，同时兼容源码与冻结(frozen)布局"""

    if getattr(sys, "frozen", False):
        frozen_root = getattr(sys, "_MEIPASS", "")
        base = (
            Path(frozen_root) if frozen_root else Path(sys.executable).resolve().parent
        )
    else:
        base = Path(__file__).resolve().parents[2]
    return base.joinpath(*(str(part) for part in parts))


def load_params(path: str | Path) -> tuple[dict[str, object], Path]:
    """加载 params.json 文件并返回其内容与所在目录"""

    source = Path(path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise PluginError(f"params.json not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PluginError(f"Invalid JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise PluginError("params.json must contain a JSON object")
    return payload, source.parent


def resolve_param_path(
    base: Path,
    value: object,
    *,
    required: bool = False,
    must_exist: bool = False,
) -> str:
    """基于 params.json 所在目录解析路径类参数"""

    if value is None or str(value).strip() == "":
        if required:
            raise PluginError("Required path field is empty")
        return ""
    raw = Path(str(value))
    resolved = raw if raw.is_absolute() else base / raw
    resolved = resolved.expanduser().resolve(strict=False)
    if must_exist and not resolved.exists():
        raise PluginError(f"Path does not exist: {resolved}")
    return str(resolved)


def parse_bool(value: object) -> bool:
    """从 HAIant 参数中解析用户填写的布尔形式"""

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off", ""}:
        return False
    raise PluginError(f"Invalid boolean value: {value}")


def _split_csv(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _int_value(
    value: object, *, default: int, label: str, minimum: int | None = None
) -> int:
    if value is None or str(value).strip() == "":
        resolved = default
    else:
        try:
            resolved = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise PluginError(f"{label} must be an integer") from exc
    if minimum is not None and resolved < minimum:
        raise PluginError(f"{label} must be >= {minimum}")
    return resolved


def _float_value(value: object, *, default: float, label: str) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PluginError(f"{label} must be a number") from exc


def _reference_index(
    params: Mapping[str, object], species: Sequence[Mapping[str, object]]
) -> int:
    value = params.get("reference")
    if value is None or str(value).strip() == "":
        return 0
    text = str(value).strip()
    if text.isdigit():
        index = int(text) - 1
    else:
        names = [str(item.get("name") or "") for item in species]
        if text not in names:
            raise PluginError(f"Reference species not found: {text}")
        index = names.index(text)
    if not 0 <= index < len(species):
        raise PluginError(f"Reference index out of range: {value}")
    return index


def _target_gene_ids(params: Mapping[str, object]) -> list[str]:
    raw = params.get("target_gene_ids")
    if raw is None or str(raw).strip() == "":
        raw = params.get("target_genes")
    return _split_csv(raw)


def _discover_species_from_input_dir(
    base: Path, input_dir: object
) -> list[dict[str, object]]:
    """镜像 platform 的自动目录物种发现(species discovery)逻辑"""

    from genomelens.analysis.requests.normalization.input_resolver import (
        discover_species_from_directory,
    )

    resolved = Path(resolve_param_path(base, input_dir, required=True, must_exist=True))
    discovered = discover_species_from_directory(resolved)
    return [asdict(item) for item in discovered]


def setup_adapter_logging(
    output_dir: str | Path, *, logger_name: str = LOGGER_NAME
) -> logging.Logger:
    """在 output_dir/run.log 下设置 adapter 日志"""

    destination = Path(output_dir).expanduser().resolve(strict=False)
    destination.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    close_logging(logger_name=logger_name)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(
        destination / "run.log", encoding="utf-8", mode="a"
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def close_logging(*, logger_name: str = LOGGER_NAME) -> None:
    """刷新并关闭 adapter 日志处理器"""

    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def close_adapter_logging(logger_name: str = LOGGER_NAME) -> None:
    """刷新并关闭 adapter 日志处理器"""

    close_logging(logger_name=logger_name)


def resolve_genomelens_exe(params: Mapping[str, object], base: Path) -> Path:
    """从 params 或环境变量中定位外部 GenomeLens 可执行文件"""

    raw = str(
        params.get("GenomeLens_Path")
        or params.get("genomelens_exe")
        or os.environ.get(GENOMELENS_EXE_ENV, "")
    ).strip()
    if not raw:
        raise PluginError(
            "GenomeLens_Path is required: set it in params.json (GenomeLens_Path or genomelens_exe) "
            "or via GENOMELENS_EXE environment variable"
        )
    path = Path(raw)
    if not path.is_absolute():
        path = (base / path).expanduser().resolve(strict=False)
    else:
        path = path.expanduser().resolve(strict=False)
    if not path.is_file():
        raise PluginError(f"GenomeLens executable not found: {path}")
    return path


def _parse_formats(value: object) -> list[str]:
    """返回选中的输出格式列表（默认 svg）

    UI 把 ``formats`` 作为单选（``customer_selector``），因此只取第一个选中的值。
    为向后兼容，列表形式也做防御性接受，但 auto 插件不打算支持多格式输出
    """

    if isinstance(value, list):
        text = str(value[0]).strip() if value else ""
    else:
        text = str(value or "").strip().split(",")[0].strip()
    return [text] if text else ["svg"]


def coerce_submodule_params(
    raw: Mapping[str, object],
    base: Path,
    declared: Sequence[tuple[str, str]],
) -> dict[str, object]:
    """将声明的子模块参数强制转换为 JSON 可用的 ``parameters`` 载荷

    ``declared`` 是 ``(param_id, ptype)`` 列表，其中 ``ptype`` 为
    ``int`` / ``float`` / ``bool`` / ``str`` / ``path`` / ``int_array`` 之一。
    缺失或留空的键会被丢弃，让子模块回退到自身默认值
    """

    out: dict[str, object] = {}
    for key, ptype in declared:
        if key not in raw:
            continue
        value = raw[key]
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        if ptype == "int":
            out[key] = _int_value(value, default=0, label=key)
        elif ptype == "float":
            out[key] = _float_value(value, default=0.0, label=key)
        elif ptype == "bool":
            out[key] = parse_bool(value)
        elif ptype == "path":
            out[key] = resolve_param_path(base, value, must_exist=True)
        elif ptype == "int_array":
            out[key] = [int(item) for item in _split_csv(value)]
        else:
            out[key] = str(value)
    return out


def write_request_json(
    output_dir: str | Path,
    request: Mapping[str, object],
    *,
    filename: str = "request.json",
) -> Path:
    """将 request JSON 写入 ``output_dir`` 并返回其路径"""

    destination = Path(output_dir).expanduser().resolve(strict=False)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / filename
    target.write_text(
        json.dumps(dict(request), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def build_run_command(
    genomelens_exe: str | Path,
    request_path: str | Path,
) -> list[str]:
    """构建 ``<GenomeLens.exe> analyze run <request.json>`` 命令行参数"""

    exe = Path(genomelens_exe)
    args = ["analyze", "run", str(request_path)]
    if exe.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(exe), *args]
    return [str(exe), *args]


def build_workflow_request(
    params: Mapping[str, object],
    base: Path,
    output_dir: str | Path,
) -> dict[str, object]:
    """为 synteny 一站式工作流构建 V3 ``WorkflowRequest`` JSON

    请求直接编码物种自动发现、参考种选择、目标基因以及全部算法/绘图选项。
    插件不再额外生成独立 engine 配置文件；这里写入的参数就是平台执行时的
    权威语义来源。
    """

    input_dir = resolve_param_path(
        base, params.get("input_dir"), required=True, must_exist=True
    )
    species = _discover_species_from_input_dir(base, input_dir)
    reference_index = _reference_index(params, species)
    target_gene_ids = _target_gene_ids(params)
    optimize_auto = parse_bool(params.get("optimize_auto", False))
    formats = _parse_formats(params.get("formats"))

    return {
        "schema_version": 3,
        "kind": "workflow_request",
        "workflow_id": "synteny",
        "species": species,
        "reference_index": reference_index,
        "inputs": {},
        "parameters": {
            "synteny": {
                "align_soft": str(params.get("align_soft") or "blast"),
                "dbtype": str(params.get("dbtype") or "nucl"),
                "cscore": _float_value(
                    params.get("cscore"), default=0.7, label="cscore"
                ),
                "dist": _int_value(params.get("dist"), default=20, label="dist"),
                "iter": _int_value(params.get("iter"), default=1, label="iter"),
                "min_block_size": _int_value(
                    params.get("min_block_size"),
                    default=1,
                    label="min_block_size",
                    minimum=1,
                ),
                "allow_simplified_fallback": False,
            },
            "local_synteny": {
                "target_gene_ids": target_gene_ids,
                "up": _int_value(params.get("up"), default=20, label="up"),
                "down": _int_value(params.get("down"), default=20, label="down"),
                "split_targets": parse_bool(params.get("split_targets", False)),
                "label_targets": parse_bool(params.get("label_targets", False)),
                "use_native_renderer": parse_bool(
                    params.get("use_native_local_synteny_renderer", False)
                ),
            },
            "plot": {
                "glyphstyle": str(params.get("glyphstyle") or ""),
                "glyphcolor": str(params.get("glyphcolor") or ""),
                "shadestyle": str(params.get("shadestyle") or ""),
                "figsize": str(params.get("figsize") or ""),
                "dpi": _int_value(
                    params.get("dpi"), default=300, label="dpi", minimum=1
                ),
                "auto_optimization": {
                    "optimize_figsize": optimize_auto,
                    "rewrite_layout_links": optimize_auto,
                    "optimize_karyotype_labels": optimize_auto,
                },
            },
        },
        "output": {
            "directory": str(output_dir),
            "force": True,
            "formats": formats,
        },
        "runtime": {
            "project_config": "",
            "engine_config": "",
            "jcvi_engine": str(params.get("jcvi_engine") or ""),
            "blastn": "",
            "makeblastdb": "",
            "lastal": "",
            "lastdb": "",
            "threads": _int_value(
                params.get("threads"), default=4, label="threads", minimum=1
            ),
            "log_level": "INFO",
            "verbose": False,
            "console_log": False,
        },
    }


def build_workflow_runtime_command(
    genomelens_exe: str | Path,
    params: Mapping[str, object],
    base: Path,
    output_dir: str | Path,
) -> list[str]:
    """写入一站式 ``WorkflowRequest`` 并返回 ``analyze run`` 命令行参数"""

    request = build_workflow_request(params, base, output_dir)
    request_path = write_request_json(
        output_dir, request, filename="workflow_request.json"
    )
    return build_run_command(genomelens_exe, request_path)


def build_submodule_request(
    module_id: str,
    inputs: Mapping[str, object],
    parameters: Mapping[str, object],
    output_dir: str | Path,
    *,
    formats: Sequence[str] | None = None,
    threads: int | None = None,
    force: bool = True,
) -> dict[str, object]:
    """为单个可编排子模块构建 V3 ``SubmoduleRequest`` JSON"""

    runtime: dict[str, object] = {
        "project_config": "",
        "engine_config": "",
        "jcvi_engine": "",
        "blastn": "",
        "makeblastdb": "",
        "lastal": "",
        "lastdb": "",
        "log_level": "INFO",
        "verbose": False,
        "console_log": False,
    }
    if threads is not None:
        runtime["threads"] = threads

    return {
        "schema_version": 3,
        "kind": "submodule_request",
        "module_id": module_id,
        "inputs": dict(inputs),
        "parameters": dict(parameters),
        "output": {
            "directory": str(output_dir),
            "force": force,
            "formats": list(formats) if formats else ["svg"],
        },
        "runtime": runtime,
    }


def build_submodule_runtime_command(
    genomelens_exe: str | Path,
    *,
    module_id: str,
    inputs: Mapping[str, object],
    parameters: Mapping[str, object],
    output_dir: str | Path,
    formats: Sequence[str] | None = None,
    threads: int | None = None,
    force: bool = True,
) -> list[str]:
    """写入 ``SubmoduleRequest`` 并返回 ``analyze run`` 命令行参数"""

    request = build_submodule_request(
        module_id,
        inputs,
        parameters,
        output_dir,
        formats=formats,
        threads=threads,
        force=force,
    )
    request_path = write_request_json(
        output_dir, request, filename="submodule_request.json"
    )
    return build_run_command(genomelens_exe, request_path)


def compress_output_intermediates(
    output_dir: str | Path,
    *,
    archive_name: str = "intermediates.zip",
    marker_name: str = "intermediates.zip.deletable",
    preserve: set[str] | None = None,
) -> Path | None:
    """将除 ``results`` 外的全部内容打包为 zip 并标记为可删除

    ``results`` 目录保持原样不动。归档后，原始中间文件与目录会被删除，
    使输出根目录仅保留 ``results``、压缩包与一个 ``.deletable`` 标记
    """

    root = Path(output_dir).expanduser().resolve(strict=False)
    if not root.is_dir():
        return None

    kept = preserve or set()
    kept = {*kept, "results", archive_name, marker_name}

    items = [path for path in root.iterdir() if path.name not in kept]
    if not items:
        return None

    archive_path = root / archive_name
    marker_path = root / marker_name

    logger = logging.getLogger(LOGGER_NAME)
    logger.info("Compressing intermediate files to %s", archive_path)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in items:
            if path.is_file():
                zf.write(path, path.name)
            elif path.is_dir():
                for child in path.rglob("*"):
                    arcname = str(child.relative_to(root)).replace("\\", "/")
                    zf.write(child, arcname)

    for path in items:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            _rm_tree(path)

    marker_path.write_text(
        "This archive contains intermediate files that can be safely deleted.\n",
        encoding="utf-8",
    )
    logger.info("Marked intermediates as deletable: %s", archive_path)
    return archive_path


def _rm_tree(path: Path) -> None:
    """递归删除目录树"""

    for child in path.iterdir():
        if child.is_dir():
            _rm_tree(child)
        else:
            child.unlink()
    path.rmdir()


def run_process(argv: Sequence[str]) -> int:
    """运行已准备好的命令并返回退出码"""

    completed = subprocess.run(list(argv), shell=False, check=False)
    return int(completed.returncode)
