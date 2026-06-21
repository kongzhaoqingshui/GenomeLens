"""GenomeLens 的 HAIant plugin adapter(智然体插件适配器)。

模块职责：
- 无参数时转发到 packaged runtime(打包运行时)，进入 workbench(工作台)。
- 有参数时读取 `params.json`，将平台字段翻译为 GenomeLens CLI(命令行接口)。
- 所有相对路径都按 `params.json` 所在目录解析。

边界：
- 不直接调用 GenomeLens 源码。
- 不实现 synteny(共线性) 算法。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path


LOGGER_NAME = "genomelens_haiant_plugin"
SUPPORTED_WORKFLOWS = {"graphics_synteny"}
RUNTIME_PASSTHROUGH_ARGS = {"-h", "--help", "--version", "help", "check", "config", "analyze", "clean", "workbench"}


class PluginError(Exception):
    """HAIant plugin adapter(智然体插件适配器) 预期失败时抛出。"""


def plugin_root() -> Path:
    """返回源码模式或打包模式下的 plugin root(插件根目录)。"""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_executable() -> Path:
    """定位已打包的 GenomeLens runtime executable(运行时可执行文件)。"""

    env = os.environ.get("GENOMELENS_PLUGIN_RUNTIME", "")
    if env:
        return Path(env).expanduser().resolve(strict=False)
    return plugin_root() / "runtime" / "GenomeLens" / "GenomeLens-runtime.exe"


def parse_bool(value: object) -> bool:
    """解析平台布尔值形式。"""

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


def resolve_param_path(
    base: Path,
    value: object,
    *,
    required: bool = False,
    must_exist: bool = False,
    fallback_bases: list[Path] | None = None,
) -> str:
    """按 `params.json` 位置解析参数路径。"""

    if value is None or str(value).strip() == "":
        if required:
            raise PluginError("Required path field is empty")
        return ""
    raw = Path(str(value))
    if raw.is_absolute():
        resolved = raw.resolve(strict=False)
        if must_exist and not resolved.exists():
            raise PluginError(f"Path does not exist: {resolved}")
        return str(resolved)

    candidates = [base / raw]
    for fallback_base in fallback_bases or []:
        candidate = fallback_base / raw
        if candidate not in candidates:
            candidates.append(candidate)

    resolved_candidates = [candidate.resolve(strict=False) for candidate in candidates]
    if must_exist:
        for candidate in resolved_candidates:
            if candidate.exists():
                return str(candidate)
        checked = "; ".join(str(candidate) for candidate in resolved_candidates)
        raise PluginError(f"Path does not exist: {checked}")
    return str(resolved_candidates[0])


def load_params(path: str | Path) -> tuple[dict[str, object], Path]:
    """加载 params JSON(参数 JSON)，并返回 payload(载荷) 与基准目录。"""

    source = Path(path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise PluginError(f"params.json not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginError(f"Invalid JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise PluginError("params.json must contain a JSON object")
    return payload, source.parent


def _formats(value: object) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [item.strip() for item in str(value or "png").split(",")]
    return [item for item in items if item] or ["png"]


def _species_from_params(
    params: dict[str, object],
    base: Path,
    mode: str,
    *,
    fallback_bases: list[Path] | None = None,
) -> list[dict[str, object]]:
    species_payload = params.get("species")
    if not isinstance(species_payload, list) or not species_payload:
        return _legacy_species_from_params(params, base, mode, fallback_bases=fallback_bases)
    species: list[dict[str, object]] = []
    for index, item in enumerate(species_payload, start=1):
        if not isinstance(item, dict):
            raise PluginError(f"species[{index}] must be an object")
        name = str(item.get("name") or f"species{index}")
        if mode == "bed_cds":
            species.append(
                {
                    "name": name,
                    "input_mode": "bed_cds",
                    "bed": resolve_param_path(
                        base,
                        item.get("bed"),
                        required=True,
                        must_exist=True,
                        fallback_bases=fallback_bases,
                    ),
                    "cds": resolve_param_path(
                        base,
                        item.get("cds"),
                        required=True,
                        must_exist=True,
                        fallback_bases=fallback_bases,
                    ),
                }
            )
        elif mode == "gff_genome":
            species.append(
                {
                    "name": name,
                    "input_mode": "gff_genome",
                    "gff": resolve_param_path(
                        base,
                        item.get("gff"),
                        required=True,
                        must_exist=True,
                        fallback_bases=fallback_bases,
                    ),
                    "genome": resolve_param_path(
                        base,
                        item.get("genome"),
                        required=True,
                        must_exist=True,
                        fallback_bases=fallback_bases,
                    ),
                }
            )
        else:
            raise PluginError(f"Unsupported input_mode: {mode}")
    if len(species) < 2:
        raise PluginError("At least two species entries are required")
    return species


def _legacy_species_from_params(
    params: dict[str, object],
    base: Path,
    mode: str,
    *,
    fallback_bases: list[Path] | None = None,
) -> list[dict[str, object]]:
    """把旧版 query/subject 参数转换成新版 species[]。"""

    query_name = str(params.get("query_name") or "query")
    subject_name = str(params.get("subject_name") or "subject")
    if mode == "bed_cds":
        legacy_fields = ["query_bed", "query_cds", "subject_bed", "subject_cds"]
        if not any(params.get(field) for field in legacy_fields):
            raise PluginError("species must contain at least two entries")
        return [
            {
                "name": query_name,
                "input_mode": "bed_cds",
                "bed": resolve_param_path(
                    base,
                    params.get("query_bed"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
                "cds": resolve_param_path(
                    base,
                    params.get("query_cds"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
            },
            {
                "name": subject_name,
                "input_mode": "bed_cds",
                "bed": resolve_param_path(
                    base,
                    params.get("subject_bed"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
                "cds": resolve_param_path(
                    base,
                    params.get("subject_cds"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
            },
        ]
    if mode == "gff_genome":
        legacy_fields = ["query_gff", "query_genome", "subject_gff", "subject_genome"]
        if not any(params.get(field) for field in legacy_fields):
            raise PluginError("species must contain at least two entries")
        return [
            {
                "name": query_name,
                "input_mode": "gff_genome",
                "gff": resolve_param_path(
                    base,
                    params.get("query_gff"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
                "genome": resolve_param_path(
                    base,
                    params.get("query_genome"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
            },
            {
                "name": subject_name,
                "input_mode": "gff_genome",
                "gff": resolve_param_path(
                    base,
                    params.get("subject_gff"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
                "genome": resolve_param_path(
                    base,
                    params.get("subject_genome"),
                    required=True,
                    must_exist=True,
                    fallback_bases=fallback_bases,
                ),
            },
        ]
    raise PluginError(f"Unsupported input_mode: {mode}")


def _optional_path(base: Path, value: object, *, fallback_bases: list[Path] | None = None) -> str:
    return resolve_param_path(base, value, must_exist=bool(value), fallback_bases=fallback_bases)


def _workflow(params: dict[str, object]) -> str:
    """返回插件允许暴露的 GenomeLens workflow"""

    workflow = str(params.get("workflow") or "graphics_synteny").strip()
    if workflow not in SUPPORTED_WORKFLOWS:
        allowed = ", ".join(sorted(SUPPORTED_WORKFLOWS))
        raise PluginError(
            f"Unsupported HAIant workflow: {workflow}. Supported workflow: {allowed}"
        )
    return workflow


def _reference_index(
    params: dict[str, object], species: list[dict[str, object]]
) -> int:
    """解析参考物种索引"""

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


def write_runtime_request(
    params: dict[str, object],
    base: Path,
    *,
    fallback_bases: list[Path] | None = None,
) -> Path:
    """写入 GenomeLens analysis request(JSON 请求)，并返回请求文件路径"""

    mode = str(params.get("input_mode") or "bed_cds")
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output", fallback_bases=fallback_bases))
    output_dir.mkdir(parents=True, exist_ok=True)
    species = _species_from_params(params, base, mode, fallback_bases=fallback_bases)
    request = {
        "schema_version": 1,
        "kind": "analysis_request",
        "method": "mcscan",
        "input": {
            "mode": mode,
            "directory": "",
            "species": species,
            "reference_index": _reference_index(params, species),
        },
        "output": {
            "directory": str(output_dir),
            "force": parse_bool(params.get("force", True)),
            "formats": _formats(params.get("formats") or "png"),
        },
        "config": {
            "project_config": _optional_path(base, params.get("config"), fallback_bases=fallback_bases),
            "method_config": _optional_path(base, params.get("jcvi_config"), fallback_bases=fallback_bases),
        },
        "options": {
            "preset": str(params.get("preset") or "auto"),
            "threads": int(params.get("threads") or 4),
            "min_block_size": int(params.get("min_block_size") or 5),
        },
        "method_config": {
            "workflow": _workflow(params),
            "jcvi_engine": _optional_path(base, params.get("jcvi_engine"), fallback_bases=fallback_bases),
            "blastn": _optional_path(base, params.get("blastn"), fallback_bases=fallback_bases),
            "makeblastdb": _optional_path(base, params.get("makeblastdb"), fallback_bases=fallback_bases),
            "jcvi_layout": _optional_path(base, params.get("jcvi_layout"), fallback_bases=fallback_bases),
            "jcvi_seqids": _optional_path(base, params.get("jcvi_seqids"), fallback_bases=fallback_bases),
            "allow_simplified_fallback": parse_bool(
                params.get("allow_simplified_fallback", False)
            ),
        },
    }
    target = output_dir / "genomelens_request.json"
    target.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def setup_adapter_logging(
    base: Path,
    output_dir_value: object,
    *,
    fallback_bases: list[Path] | None = None,
) -> logging.Logger:
    """参数可用时，在 `output_dir/run.log` 下设置 adapter logs(适配器日志)。"""

    output_dir = Path(resolve_param_path(base, output_dir_value or "output", fallback_bases=fallback_bases))
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "run.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    close_adapter_logging()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def close_adapter_logging() -> None:
    """Flush and close HAIant adapter logging handlers."""

    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def _build_runtime_command(params_path: str | Path) -> list[str]:
    """把 `params.json` 转换为 GenomeLens runtime argv(运行时参数向量)。

    插件只依赖公开 `analyze run <request.json>` 入口；具体分析逻辑由 GenomeLens
    runtime 根据稳定 AnalysisRequest 协议调度。
    """

    params, params_base = load_params(params_path)
    base = plugin_root()
    fallback_bases = [params_base]
    logger = setup_adapter_logging(base, params.get("output_dir"), fallback_bases=fallback_bases)
    logger.info("Loaded params.json: %s", params_path)
    runtime = runtime_executable()
    if not runtime.is_file():
        raise PluginError(f"GenomeLens runtime executable not found: {runtime}")

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output", fallback_bases=fallback_bases))
    output_dir.mkdir(parents=True, exist_ok=True)
    request_path = write_runtime_request(params, base, fallback_bases=fallback_bases)
    argv = [str(runtime), "analyze", "run", str(request_path)]

    logger.info("Dispatching GenomeLens runtime: %s", argv)
    return argv


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build GenomeLens runtime argv and release adapter log handles."""

    try:
        return _build_runtime_command(params_path)
    finally:
        close_adapter_logging()


def run_runtime(argv: list[str]) -> int:
    """运行已打包 runtime(运行时)，并返回退出码。"""

    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def is_runtime_cli_invocation(argv: list[str]) -> bool:
    """判断参数是否应作为 runtime CLI 命令透传，而不是当作 params.json。"""

    return bool(argv) and argv[0] in RUNTIME_PASSTHROUGH_ARGS


def main(argv: list[str] | None = None) -> int:
    """plugin executable(插件可执行文件) 入口。"""

    if argv is None:
        argv = sys.argv[1:]
    try:
        runtime = runtime_executable()
        if not argv:
            if not runtime.is_file():
                raise PluginError(f"GenomeLens runtime executable not found: {runtime}")
            return run_runtime([str(runtime)])
        if is_runtime_cli_invocation(argv):
            if not runtime.is_file():
                raise PluginError(f"GenomeLens runtime executable not found: {runtime}")
            return run_runtime([str(runtime), *argv])
        if len(argv) != 1:
            raise PluginError("Expected zero arguments or one params.json path")
        return run_runtime(build_runtime_command(argv[0]))
    except PluginError as exc:
        print(f"GenomeLens HAIant plugin error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
