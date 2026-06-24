"""读取并校验 engine manifest JSON(引擎清单 JSON)"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from jcvi_genomelens.manifest.models import (
    EngineEdge,
    EngineRunManifest,
    EngineTrack,
    GenomeSpec,
    ToolchainSpec,
    WorkflowOptions,
)
from jcvi_genomelens.workflows.contract import (
    GLOBAL_KARYOTYPE_WORKFLOW,
    HEATMAP_WORKFLOW,
    HISTOGRAM_WORKFLOW,
    MULTI_LOCAL_SYNTENY_WORKFLOW,
    normalize_workflow,
)

# endregion


class ManifestError(ValueError):
    """manifest(清单) 违反公开契约时抛出"""


def _path(value: object, *, required: bool = False) -> Path | None:
    if value is None or str(value).strip() == "":
        if required:
            raise ManifestError("required path field is empty")
        return None
    # engine 侧统一把 manifest 路径绝对化，后续 workflow 内不再猜工作目录。
    return Path(str(value)).expanduser().resolve(strict=False)


def _require_object(data: object, label: str) -> dict[str, object]:
    if not isinstance(data, dict):
        raise ManifestError(f"{label} must be an object")
    return data


def _optional_object(data: object, label: str) -> dict[str, object]:
    if data is None:
        return {}
    return _require_object(data, label)


def _optional_object_list(data: object, label: str) -> list[dict[str, object]]:
    if data is None:
        return []
    if not isinstance(data, list):
        raise ManifestError(f"{label} must be a list")
    items: list[dict[str, object]] = []
    for index, item in enumerate(data):
        # 这里保留原始 object 结构，摘要写回时能原样传给 shell。
        items.append(_require_object(item, f"{label}[{index}]"))
    return items


def _optional_string_list(data: object, label: str) -> list[str]:
    if data is None:
        return []
    if not isinstance(data, list):
        raise ManifestError(f"{label} must be a list")
    return [str(item) for item in data]


def _float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"invalid float value: {value}") from exc


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return _float(value, 0.0)


def _int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"invalid integer value: {value}") from exc


def _string(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ManifestError(f"invalid string list value: {value}")


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off", ""}:
        return False
    raise ManifestError(f"invalid boolean value: {value}")


def _bool_dict(value: object) -> dict[str, bool]:
    raw = _optional_object(value, "bool dict")
    result: dict[str, bool] = {}
    for key, val in raw.items():
        result[str(key)] = _bool(val)
    return result


def _histogram_columns(value: object) -> list[int]:
    raw = _string_list(value)
    if raw:
        return [_int(item, 0) for item in raw]
    return [0]


def _load_genome(data: object, label: str) -> GenomeSpec:
    raw = _require_object(data, label)
    name = str(raw.get("name") or label)
    bed = _path(raw.get("bed"), required=True)
    cds = _path(raw.get("cds"), required=True)
    assert bed is not None and cds is not None
    if not bed.is_file():
        raise ManifestError(f"{label}.bed does not exist: {bed}")
    if not cds.is_file():
        raise ManifestError(f"{label}.cds does not exist: {cds}")
    # manifest 读取阶段就把文件存在性卡死，避免 workflow 跑到中途才炸。
    return GenomeSpec(name=name, bed=bed, cds=cds)


def _load_track(data: object, label: str) -> EngineTrack:
    raw = _require_object(data, label)
    name = str(raw.get("name") or label)
    bed = _path(raw.get("bed"), required=True)
    assert bed is not None
    if not bed.is_file():
        raise ManifestError(f"{label}.bed does not exist: {bed}")
    return EngineTrack(name=name, bed=bed)


def _load_edge(data: object, label: str, track_count: int) -> EngineEdge:
    raw = _require_object(data, label)
    try:
        i = int(raw.get("i"))  # type: ignore[arg-type]
        j = int(raw.get("j"))  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{label}.i/.j must be integers") from exc
    if not (0 <= i < track_count) or not (0 <= j < track_count):
        raise ManifestError(f"{label} references track index out of range: i={i}, j={j}")
    simple = _path(raw.get("simple"), required=True)
    assert simple is not None
    if not simple.is_file():
        raise ManifestError(f"{label}.simple does not exist: {simple}")
    return EngineEdge(i=i, j=j, simple=simple)


def _load_precomputed_path(data: object, label: str) -> Path:
    path = _path(data, required=True)
    assert path is not None
    if not path.is_file():
        raise ManifestError(f"{label} does not exist: {path}")
    return path


def _load_existing_paths(data: object, label: str) -> list[Path]:
    if not isinstance(data, list) or not data:
        raise ManifestError(f"{label} must be a non-empty list")
    paths: list[Path] = []
    for index, item in enumerate(data):
        path = _path(item, required=True)
        assert path is not None
        if not path.is_file():
            raise ManifestError(f"{label}[{index}] does not exist: {path}")
        paths.append(path)
    return paths


def load_manifest(path: str | Path) -> EngineRunManifest:
    """从磁盘加载并校验 manifest(清单)"""

    source = Path(path).expanduser().resolve(strict=False)
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    raw = _require_object(data, "manifest")
    workflow = normalize_workflow(str(raw.get("workflow") or ""))
    if not workflow:
        raise ManifestError("workflow is required")
    schema_version = _int(raw.get("schema_version"), 3)
    if schema_version != 3:
        raise ManifestError(f"unsupported manifest schema_version: {schema_version}")
    inputs_raw = _require_object(raw.get("inputs") or {}, "inputs")
    toolchain_raw = _require_object(raw.get("toolchain") or {}, "toolchain")
    options_raw = _require_object(raw.get("parameters") or {}, "parameters")
    formats = options_raw.get("formats") or ["svg"]
    if not isinstance(formats, list):
        raise ManifestError("options.formats must be a list")
    allow_simplified_fallback = _bool(options_raw.get("allow_simplified_fallback", False))
    if allow_simplified_fallback:
        raise ManifestError("allow_simplified_fallback is not implemented for production JCVI workflows")
    rowgroups = _path(options_raw.get("rowgroups"))
    if rowgroups is not None and not rowgroups.is_file():
        raise ManifestError(f"options.rowgroups does not exist: {rowgroups}")

    # manifest v3 中 pairwise 输入来自 inputs.species[0:2]；query/subject 只作为
    # engine 内部执行对象名。全局总图工作流用 tracks/edges 表达 N 个物种。
    query: GenomeSpec | None = None
    subject: GenomeSpec | None = None
    tracks: list[EngineTrack] = []
    edges: list[EngineEdge] = []
    blocks: Path | None = None
    bed: Path | None = None
    matrix: Path | None = None
    histogram_inputs: list[Path] = []
    if workflow == GLOBAL_KARYOTYPE_WORKFLOW:
        track_data = inputs_raw.get("tracks")
        if not isinstance(track_data, list) or len(track_data) < 2:
            raise ManifestError("graphics_karyotype_global requires at least two tracks")
        # 全局核型图直接消费 pairwise 阶段产出的轨道和边，协议形状与 pairwise 不同。
        tracks = [_load_track(item, f"tracks[{index}]") for index, item in enumerate(track_data)]
        edge_data = inputs_raw.get("edges")
        if not isinstance(edge_data, list) or not edge_data:
            raise ManifestError("graphics_karyotype_global requires at least one edge")
        edges = [_load_edge(item, f"edges[{index}]", len(tracks)) for index, item in enumerate(edge_data)]
    elif workflow == MULTI_LOCAL_SYNTENY_WORKFLOW:
        track_data = inputs_raw.get("tracks")
        if not isinstance(track_data, list) or len(track_data) < 2:
            raise ManifestError("local_synteny_multi requires at least two tracks")
        tracks = [_load_track(item, f"tracks[{index}]") for index, item in enumerate(track_data)]
        blocks = _load_precomputed_path(inputs_raw.get("blocks"), "inputs.blocks")
        bed = _load_precomputed_path(inputs_raw.get("bed"), "inputs.bed")
    elif workflow == HEATMAP_WORKFLOW:
        matrix = _load_precomputed_path(inputs_raw.get("matrix"), "inputs.matrix")
    elif workflow == HISTOGRAM_WORKFLOW:
        histogram_inputs = _load_existing_paths(inputs_raw.get("histogram_files"), "inputs.histogram_files")
    else:
        species_data = inputs_raw.get("species")
        if not isinstance(species_data, list) or len(species_data) < 2:
            raise ManifestError("pairwise workflows require inputs.species with at least two species")
        query = _load_genome(species_data[0], "inputs.species[0]")
        subject = _load_genome(species_data[1], "inputs.species[1]")

    return EngineRunManifest(
        workflow=workflow,
        query=query,
        subject=subject,
        toolchain=ToolchainSpec(
            blastn=_path(toolchain_raw.get("blastn")),
            makeblastdb=_path(toolchain_raw.get("makeblastdb")),
            lastal=_path(toolchain_raw.get("lastal")),
            lastdb=_path(toolchain_raw.get("lastdb")),
        ),
        options=WorkflowOptions(
            threads=_int(options_raw.get("threads"), 4),
            min_block_size=_int(options_raw.get("min_block_size"), 5),
            formats=list(formats),
            layout=_path(options_raw.get("layout")),
            seqids=_path(options_raw.get("seqids")),
            allow_simplified_fallback=allow_simplified_fallback,
            align_soft=_string(options_raw.get("align_soft"), "blast"),
            dbtype=_string(options_raw.get("dbtype"), "nucl"),
            cscore=_float(options_raw.get("cscore"), 0.7),
            dist=_int(options_raw.get("dist"), 20),
            iter=_int(options_raw.get("iter"), 1),
            target_gene_ids=_string_list(options_raw.get("target_gene_ids")),
            up=_int(options_raw.get("up"), 20),
            down=_int(options_raw.get("down"), 20),
            split_targets=_bool(options_raw.get("split_targets", False)),
            label_targets=_bool(options_raw.get("label_targets", False)),
            glyphstyle=_string(options_raw.get("glyphstyle"), ""),
            glyphcolor=_string(options_raw.get("glyphcolor"), ""),
            shadestyle=_string(options_raw.get("shadestyle"), ""),
            figsize=_string(options_raw.get("figsize"), ""),
            dpi=_int(options_raw.get("dpi"), 300),
            cmap=_string(options_raw.get("cmap"), ""),
            groups=_bool(options_raw.get("groups", False)),
            rowgroups=rowgroups,
            horizontalbar=_bool(options_raw.get("horizontalbar", False)),
            log_level=_string(options_raw.get("log_level"), "INFO"),
            verbose=_bool(options_raw.get("verbose", False)),
            auto_optimization=_bool_dict(options_raw.get("auto_optimization")),
            use_native_local_synteny_renderer=_bool(options_raw.get("use_native_local_synteny_renderer", False)),
            histogram_inputs=histogram_inputs,
            histogram_columns=_histogram_columns(options_raw.get("histogram_columns")),
            histogram_skip=_int(options_raw.get("histogram_skip"), 0),
            histogram_bins=_int(options_raw.get("histogram_bins"), 20),
            histogram_vmin=_optional_float(options_raw.get("histogram_vmin")),
            histogram_vmax=_optional_float(options_raw.get("histogram_vmax")),
            histogram_xlabel=_string(options_raw.get("histogram_xlabel"), "value"),
            histogram_title=_string(options_raw.get("histogram_title"), ""),
            histogram_base=_int(options_raw.get("histogram_base"), 0),
            histogram_facet=_bool(options_raw.get("histogram_facet", False)),
            histogram_fill=_string(options_raw.get("histogram_fill"), "white"),
        ),
        schema_version=schema_version,
        # task/species/meta 保持宽松对象结构，供 shell summary 直接回写。
        task=_optional_object(raw.get("task"), "task"),
        species=_optional_object_list(raw.get("species") or inputs_raw.get("species"), "species"),
        expected_outputs=_optional_string_list(raw.get("expected_outputs"), "expected_outputs"),
        meta=_require_object(raw.get("meta") or {}, "meta"),
        tracks=tracks,
        edges=edges,
        blocks=blocks,
        bed=bed,
        matrix=matrix,
    )
