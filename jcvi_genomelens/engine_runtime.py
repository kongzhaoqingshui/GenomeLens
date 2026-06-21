"""engine runtime(引擎运行时) 入口辅助模块"""

# region import
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from jcvi_genomelens.manifest_loader import load_manifest
from jcvi_genomelens.manifest_models import EngineEdge, EngineRunManifest, EngineTrack, GenomeSpec
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.runtime.logging_utils import close_engine_logging, set_engine_log_level, setup_engine_logging
from jcvi_genomelens.runtime.summary_writer import write_summary
from jcvi_genomelens.runtime.task_log import task_scope
from jcvi_genomelens.workflow_dispatcher import dispatch

# endregion


def _is_ascii_path(path: Path | None) -> bool:
    """Return whether a path is safe for legacy BLAST/JCVI text handling."""

    return path is None or all(ord(char) < 128 for char in str(path))


def _manifest_paths(manifest: EngineRunManifest, outdir: Path) -> list[Path]:
    paths: list[Path] = [outdir]
    if manifest.query is not None:
        paths.extend([manifest.query.bed, manifest.query.cds])
    if manifest.subject is not None:
        paths.extend([manifest.subject.bed, manifest.subject.cds])
    if manifest.options.layout is not None:
        paths.append(manifest.options.layout)
    if manifest.options.seqids is not None:
        paths.append(manifest.options.seqids)
    paths.extend(track.bed for track in manifest.tracks)
    paths.extend(edge.simple for edge in manifest.edges)
    if manifest.blocks is not None:
        paths.append(manifest.blocks)
    if manifest.bed is not None:
        paths.append(manifest.bed)
    return paths


def _needs_ascii_workdir(manifest: EngineRunManifest, outdir: Path) -> bool:
    return os.name == "nt" and any(not _is_ascii_path(path) for path in _manifest_paths(manifest, outdir))


def _copy_input(path: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return target


def _stage_genome(spec: GenomeSpec | None, inputs: Path, prefix: str) -> GenomeSpec | None:
    if spec is None:
        return None
    return GenomeSpec(
        name=spec.name,
        bed=_copy_input(spec.bed, inputs / f"{prefix}.bed"),
        cds=_copy_input(spec.cds, inputs / f"{prefix}.cds"),
    )


def _stage_manifest(manifest: EngineRunManifest, work_root: Path) -> EngineRunManifest:
    inputs = work_root / "inputs"
    query = _stage_genome(manifest.query, inputs, "query")
    subject = _stage_genome(manifest.subject, inputs, "subject")
    tracks = [
        EngineTrack(name=track.name, bed=_copy_input(track.bed, inputs / "tracks" / f"track_{index}.bed"))
        for index, track in enumerate(manifest.tracks)
    ]
    edges = [
        EngineEdge(i=edge.i, j=edge.j, simple=_copy_input(edge.simple, inputs / "edges" / f"edge_{index}.simple"))
        for index, edge in enumerate(manifest.edges)
    ]
    options = replace(
        manifest.options,
        layout=_copy_input(manifest.options.layout, inputs / "layout.txt") if manifest.options.layout else None,
        seqids=_copy_input(manifest.options.seqids, inputs / "seqids.txt") if manifest.options.seqids else None,
    )
    blocks = _copy_input(manifest.blocks, inputs / "blocks.txt") if manifest.blocks else None
    bed = _copy_input(manifest.bed, inputs / "all.bed") if manifest.bed else None
    return replace(
        manifest,
        query=query,
        subject=subject,
        options=options,
        tracks=tracks,
        edges=edges,
        blocks=blocks,
        bed=bed,
    )


def _copy_workdir_to_output(work_root: Path, outdir: Path) -> None:
    for item in work_root.iterdir():
        target = outdir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _map_path_string(value: str, source_root: Path, target_root: Path) -> str:
    try:
        path = Path(value).resolve(strict=False)
        relative = path.relative_to(source_root.resolve(strict=False))
    except (OSError, ValueError):
        return value
    return str((target_root / relative).resolve(strict=False))


def _map_paths(value: object, source_root: Path, target_root: Path) -> object:
    if isinstance(value, str):
        return _map_path_string(value, source_root, target_root)
    if isinstance(value, list):
        return [_map_paths(item, source_root, target_root) for item in value]
    if isinstance(value, dict):
        return {key: _map_paths(item, source_root, target_root) for key, item in value.items()}
    return value


def _map_commands(commands: list[CommandAudit], source_root: Path, target_root: Path) -> list[CommandAudit]:
    return [
        CommandAudit(
            name=command.name,
            argv=[_map_path_string(arg, source_root, target_root) for arg in command.argv],
            returncode=command.returncode,
            cwd=_map_path_string(command.cwd, source_root, target_root) if command.cwd else "",
            stdout=command.stdout,
            stderr=command.stderr,
        )
        for command in commands
    ]


def _ascii_temp_parent() -> Path | None:
    candidates: list[Path] = []
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        if local_appdata:
            candidates.append(Path(local_appdata) / "Temp")
        candidates.append(Path(system_root) / "Temp")
    candidates.append(Path(tempfile.gettempdir()))
    for candidate in candidates:
        if _is_ascii_path(candidate):
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    return None


def _dispatch_with_ascii_workdir(
    manifest: EngineRunManifest,
    outdir: Path,
) -> tuple[list[CommandAudit], dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="genomelens-engine-", dir=_ascii_temp_parent()) as tmpdir:
        work_root = Path(tmpdir).resolve(strict=False)
        staged_manifest = _stage_manifest(manifest, work_root)
        commands, artifacts = dispatch(staged_manifest, work_root)
        _copy_workdir_to_output(work_root, outdir)
        mapped_artifacts = _map_paths(artifacts, work_root, outdir)
        if not isinstance(mapped_artifacts, dict):
            raise RuntimeError("Engine artifacts must be a mapping")
        return _map_commands(commands, work_root, outdir), mapped_artifacts


def run_manifest(manifest_path: str | Path, outdir: str | Path) -> Path:
    """运行 manifest(清单) 并写出 `engine_run_summary.json`"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    log_path = root / "run.log"
    logger = setup_engine_logging(log_path)
    workflow = "unknown"
    manifest = None
    try:
        # 先解析 manifest，再把 workflow 名称传播到日志和最终摘要。
        with task_scope(task_id="engine", step="load_manifest", context={"manifest": str(manifest_path)}):
            manifest = load_manifest(manifest_path)
        workflow = manifest.workflow
        set_engine_log_level(manifest.options.log_level)
        logger.info("Running workflow %s", manifest.workflow)
        with task_scope(task_id="engine", step=f"dispatch_{manifest.workflow}", context={"outdir": str(root)}):
            if _needs_ascii_workdir(manifest, root):
                logger.info("Using ASCII staging directory for BLAST/JCVI path compatibility")
                commands, artifacts = _dispatch_with_ascii_workdir(manifest, root)
            else:
                commands, artifacts = dispatch(manifest, root)
        return write_summary(
            root / "engine_run_summary.json",
            status="ok",
            workflow=manifest.workflow,
            commands=commands,
            artifacts=artifacts,
            logs={"run_log": str(log_path)},
            schema_version=manifest.schema_version,
            task=manifest.task,
            species=manifest.species,
            expected_outputs=manifest.expected_outputs,
            error=None,
        )
    except Exception as exc:
        logger.exception("Engine run failed")
        manifest_kwargs = {}
        if manifest is not None:
            # manifest 已可用时，失败摘要也尽量保留任务上下文，便于 shell 层复盘。
            manifest_kwargs = {
                "schema_version": manifest.schema_version,
                "task": manifest.task,
                "species": manifest.species,
                "expected_outputs": manifest.expected_outputs,
            }
        return write_summary(
            root / "engine_run_summary.json",
            status="failed",
            workflow=workflow,
            commands=[],
            artifacts={},
            logs={"run_log": str(log_path)},
            **manifest_kwargs,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
    finally:
        close_engine_logging()
