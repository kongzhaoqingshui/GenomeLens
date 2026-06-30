"""由 BLAST+ / LAST / Diamond 和 vendored JCVI(随包 JCVI) 支撑的真实 pairwise MCscan workflow(成对 MCscan 工作流)"""

# region import
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from jcvi.compara.synteny import mcscan as jcvi_mcscan
from jcvi.compara.synteny import scan as jcvi_scan
from jcvi.compara.synteny import simple as jcvi_simple
from jcvi.formats.bed import merge as jcvi_bed_merge
from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_command, run_python_step
from jcvi_genomelens.runtime.path_utils import short_path
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.pairwise import catalog_ortholog

# endregion


def _required_tool(path: Path | None, label: str) -> str:
    """返回必需 executable(可执行文件) 路径，或抛出清晰错误"""

    if path is None or not path.is_file():
        raise FileNotFoundError(f"{label} executable not found: {path}")
    return str(path)


def _write_default_layout(path: Path, query_label: str, subject_label: str) -> Path:
    """写出适用于 JCVI `graphics.synteny` 的双轨 layout(布局)"""

    path.write_text(
        "\n".join(
            [
                "# x, y, rotation, ha, va, color, ratio, label",
                f"0.50, 0.70, 0, center, top, #2f6f73, 1, {query_label}",
                f"0.50, 0.30, 0, center, bottom, #b85c38, 1, {subject_label}",
                "e, 0, 1, #c8c8c8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _normalize_simple_name(generated_simple: Path, expected_simple: Path) -> Path:
    """JCVI 写出 `<prefix>.simple`；GenomeLens 发布 `<prefix>.anchors.simple`"""

    if generated_simple.is_file() and generated_simple != expected_simple:
        # JCVI 默认文件名与 GenomeLens 对外发布名不同，重命名为稳定发布名
        shutil.move(str(generated_simple), str(expected_simple))
    if expected_simple.is_file():
        return expected_simple
    return generated_simple


def _ensure_nonempty(path: Path, label: str) -> None:
    """确认产物文件非空，否则抛出明确错误"""

    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} output is empty: {path}")


def _run_blast_pair(
    manifest: EngineRunManifest,
    root: Path,
    blast_table: Path,
) -> tuple[CommandAudit, CommandAudit]:
    """运行 makeblastdb + blastn。

    Windows 上 BLAST+ 仍使用 ANSI argv，中文/特殊字符路径会被破坏。因此
    在 Windows 下把输入 FASTA 拷到系统临时目录（路径通常为 ASCII），数据库和
    中间表也在该目录生成，最后把 blast 表移回目标位置；非 Windows 系统直接
    在目标目录运行，避免不必要的拷贝。
    """

    if manifest.query is None or manifest.subject is None:
        raise ValueError("blast step requires query and subject species")

    makeblastdb = short_path(_required_tool(manifest.toolchain.makeblastdb, "makeblastdb"))
    blastn = short_path(_required_tool(manifest.toolchain.blastn, "blastn"))
    threads = max(1, manifest.options.threads)

    if os.name != "nt":
        db_prefix = root / "blast_db"
        makeblastdb_cmd = run_command(
            [
                makeblastdb,
                "-in",
                str(manifest.subject.cds),
                "-dbtype",
                "nucl",
                "-out",
                str(db_prefix),
            ],
            cwd=str(root),
        )
        _assert_ok(makeblastdb_cmd)

        blastn_cmd = run_command(
            [
                blastn,
                "-query",
                str(manifest.query.cds),
                "-db",
                str(db_prefix),
                "-out",
                str(blast_table),
                "-outfmt",
                "6",
                "-num_threads",
                str(threads),
            ],
            cwd=str(root),
            timeout=3600,
        )
        _assert_ok(blastn_cmd)
        _ensure_nonempty(blast_table, "BLAST")
        for suffix in (".nhr", ".nin", ".nsq"):
            scratch = db_prefix.with_suffix(suffix)
            if scratch.is_file():
                scratch.unlink()
        if db_prefix.is_file():
            db_prefix.unlink()
        return makeblastdb_cmd, blastn_cmd

    with tempfile.TemporaryDirectory(prefix="glblast_") as tmp:
        tmpdir = Path(tmp)
        subject_cds = tmpdir / "subject.cds"
        query_cds = tmpdir / "query.cds"
        db_prefix = tmpdir / "db"
        blast_out = tmpdir / "blast.tsv"

        shutil.copy2(manifest.subject.cds, subject_cds)
        shutil.copy2(manifest.query.cds, query_cds)

        makeblastdb_cmd = run_command(
            [
                makeblastdb,
                "-in",
                str(subject_cds),
                "-dbtype",
                "nucl",
                "-out",
                str(db_prefix),
            ],
            cwd=str(tmpdir),
        )
        _assert_ok(makeblastdb_cmd)

        blastn_cmd = run_command(
            [
                blastn,
                "-query",
                str(query_cds),
                "-db",
                str(db_prefix),
                "-out",
                str(blast_out),
                "-outfmt",
                "6",
                "-num_threads",
                str(threads),
            ],
            cwd=str(tmpdir),
            timeout=3600,
        )
        _assert_ok(blastn_cmd)
        _ensure_nonempty(blast_out, "BLAST")

        blast_table.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(blast_out), str(blast_table))
        return makeblastdb_cmd, blastn_cmd


def _run_scan(
    manifest: EngineRunManifest,
    root: Path,
    blast_table: Path,
    anchors: Path,
) -> CommandAudit:
    """从 blast 表生成 anchors"""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("scan step requires query and subject species")

    # min_size/dist 在 engine 边界再做一次下限保护，避免异常配置穿透到 JCVI
    min_size = max(1, manifest.options.min_block_size)
    dist = max(1, manifest.options.dist)
    cmd = run_python_step(
        "jcvi.compara.synteny.scan",
        jcvi_scan,
        [
            str(blast_table),
            str(anchors),
            f"--qbed={manifest.query.bed}",
            f"--sbed={manifest.subject.bed}",
            f"--min_size={min_size}",
            f"--dist={dist}",
            "--no_strip_names",
        ],
        cwd=root,
    )
    _assert_ok(cmd)
    _ensure_nonempty(anchors, "JCVI anchors")
    return cmd


def _run_simple(
    manifest: EngineRunManifest,
    root: Path,
    anchors: Path,
    generated_simple: Path,
    simple: Path,
) -> CommandAudit:
    """从 anchors 生成 simple 文件"""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("simple step requires query and subject species")

    cmd = run_python_step(
        "jcvi.compara.synteny.simple",
        jcvi_simple,
        [
            str(anchors),
            f"--qbed={manifest.query.bed}",
            f"--sbed={manifest.subject.bed}",
        ],
        cwd=root,
    )
    _assert_ok(cmd)
    actual_simple = _normalize_simple_name(generated_simple, simple)
    _ensure_nonempty(actual_simple, "JCVI simple")
    return cmd


def _run_mcscan(
    manifest: EngineRunManifest,
    root: Path,
    anchors: Path,
    blocks: Path,
) -> CommandAudit:
    """从 anchors 生成 blocks"""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("mcscan step requires query and subject species")

    iter_count = max(1, manifest.options.iter)
    cmd = run_python_step(
        "jcvi.compara.synteny.mcscan",
        jcvi_mcscan,
        [str(manifest.query.bed), str(anchors), f"--iter={iter_count}", "-o", str(blocks)],
        cwd=root,
    )
    _assert_ok(cmd)
    _ensure_nonempty(blocks, "JCVI blocks")
    return cmd


def _run_merge_bed(
    manifest: EngineRunManifest,
    root: Path,
    merged_bed: Path,
) -> CommandAudit:
    """合并 query 与 subject bed 为 all.bed"""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("bed merge step requires query and subject species")

    cmd = run_python_step(
        "jcvi.formats.bed.merge",
        jcvi_bed_merge,
        [str(manifest.query.bed), str(manifest.subject.bed), "-o", str(merged_bed)],
        cwd=root,
    )
    _assert_ok(cmd)
    _ensure_nonempty(merged_bed, "Merged BED")
    return cmd


def _run_with_blast(manifest: EngineRunManifest, root: Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """使用 BLAST+ 运行 pairwise MCscan 并返回标准 artifacts"""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("blast pairwise workflow requires query and subject species")

    blast_table = root / "blast.tsv"
    anchors = root / "anchors"
    generated_simple = root / "anchors.simple"
    simple = root / "anchors.simple"
    blocks = root / "blocks"
    merged_bed = root / "all.bed"

    # BLAST 路径走原生命令，scan/simple/mcscan 走进程内 JCVI 函数，最后统一归档
    commands: list[CommandAudit] = []
    makeblastdb_cmd, blastn_cmd = _run_blast_pair(manifest, root, blast_table)
    commands.extend([makeblastdb_cmd, blastn_cmd])
    commands.append(_run_scan(manifest, root, blast_table, anchors))
    commands.append(_run_simple(manifest, root, anchors, generated_simple, simple))
    commands.append(_run_mcscan(manifest, root, anchors, blocks))
    commands.append(_run_merge_bed(manifest, root, merged_bed))

    return commands, {
        "blast_table": str(blast_table),
        "anchors": str(anchors),
        "simple": str(simple),
        "blocks": str(blocks),
        "merged_bed": str(merged_bed),
    }


def _run_with_catalog(
    manifest: EngineRunManifest, root: Path, *, emit_ortholog: bool = False
) -> tuple[list[CommandAudit], dict[str, object]]:
    """使用 JCVI catalog.ortholog（支持 LAST / Diamond）运行 pairwise 并返回标准 artifacts

    ``emit_ortholog`` 为真时，额外把双向 ortholog 目录透传到返回的 artifact 字典。
    """

    if manifest.query is None or manifest.subject is None:
        raise ValueError("catalog pairwise workflow requires query and subject species")

    # LAST / Diamond 直接复用 catalog workflow，避免在这里重复维护同源搜索细节
    catalog_commands, catalog_artifacts = catalog_ortholog.run(manifest, root)
    prefix = f"{manifest.query.name}.{manifest.subject.name}"
    merged_bed = root / "all.bed"
    merge_cmd = run_python_step(
        "jcvi.formats.bed.merge",
        jcvi_bed_merge,
        [str(manifest.query.bed), str(manifest.subject.bed), "-o", str(merged_bed)],
        cwd=root,
    )
    _assert_ok(merge_cmd)
    if not merged_bed.is_file() or merged_bed.stat().st_size == 0:
        raise RuntimeError(f"Merged BED output is empty: {merged_bed}")

    blast_table = catalog_artifacts.get("blast_table") or str(root / f"{prefix}.last")
    anchors = catalog_artifacts.get("anchors") or str(root / f"{prefix}.anchors")
    blocks = catalog_artifacts.get("blocks") or str(root / f"{prefix}.1x1.blocks")
    simple = catalog_artifacts.get("lifted_anchors") or anchors

    artifacts: dict[str, object] = {
        "blast_table": str(blast_table),
        "anchors": str(anchors),
        "simple": str(simple),
        "blocks": str(blocks),
        "merged_bed": str(merged_bed),
    }
    if emit_ortholog:
        for key in ("ortholog", "reverse_ortholog"):
            value = catalog_artifacts.get(key)
            if value:
                artifacts[key] = str(value)
    return catalog_commands + [merge_cmd], artifacts


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行真实 pairwise MCscan 步骤

    workflow(工作流)：
    - align_soft == "blast" 时：makeblastdb -> blastn -> scan -> simple -> mcscan。
    - align_soft 为 "last" 或 "diamond_blastp" 时：复用 JCVI catalog.ortholog。
    """

    if manifest.query is None or manifest.subject is None:
        raise ValueError("pairwise MCscan workflow requires query and subject species")

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    # graphics.synteny 需要 layout；用户没给时这里生成一个稳定的默认双轨布局
    layout = manifest.options.layout if manifest.options.layout else root / "synteny.layout"
    if manifest.options.layout is None:
        _write_default_layout(layout, manifest.query.name, manifest.subject.name)

    align_soft = manifest.options.align_soft or "blast"
    emit_ortholog = manifest.options.emit_ortholog
    # ortholog 目录只能由 catalog 后端产出；用户要 ortholog 时强制走 catalog 路径
    if emit_ortholog or align_soft in {"last", "diamond_blastp"}:
        commands, pairwise_artifacts = _run_with_catalog(manifest, root, emit_ortholog=emit_ortholog)
    elif align_soft == "blast":
        commands, pairwise_artifacts = _run_with_blast(manifest, root)
    else:
        raise ValueError(f"unsupported align_soft: {align_soft}")

    # pairwise 结果先收敛为统一 artifact 字典，供 graphics/local 等后续 workflow 继续消费
    artifacts = {
        **pairwise_artifacts,
        "layout": str(layout),
        "figures": [],
        "simplified_fallback": False,
        "backend": "jcvi",
    }
    return commands, artifacts
