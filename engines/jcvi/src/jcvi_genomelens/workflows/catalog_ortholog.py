"""真实 JCVI `catalog.ortholog` workflow(工作流)"""

# region import
from __future__ import annotations

import contextlib
import os
import shutil
from pathlib import Path

import jcvi.compara.catalog as jcvi_catalog
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok

# endregion


@contextlib.contextmanager
def _blast_path_injected(manifest: EngineRunManifest):
    """把 BLAST+ 目录临时注入 PATH，让 JCVI 按名字调用 blastn/makeblastdb。"""

    old_path = os.environ.get("PATH", "")
    blast_dir = str(manifest.toolchain.blastn.parent) if manifest.toolchain.blastn else ""
    if blast_dir:
        os.environ["PATH"] = blast_dir + os.pathsep + old_path
    try:
        yield
    finally:
        os.environ["PATH"] = old_path


def _copy_inputs_for_catalog(manifest: EngineRunManifest, root: Path) -> tuple[str, str]:
    """JCVI `catalog.ortholog` 期望在 cwd(当前目录) 中存在 `<species>.bed` 和 `<species>.cds`"""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("catalog.ortholog requires query and subject species")

    query = manifest.query.name
    subject = manifest.subject.name
    # catalog.ortholog 假设文件名由物种名推导，所以先把输入复制成 JCVI 期望命名。
    shutil.copy2(manifest.query.bed, root / f"{query}.bed")
    shutil.copy2(manifest.query.cds, root / f"{query}.cds")
    shutil.copy2(manifest.subject.bed, root / f"{subject}.bed")
    shutil.copy2(manifest.subject.cds, root / f"{subject}.cds")
    return query, subject


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """以 full mode(完整模式) 运行 JCVI `catalog.ortholog`，并返回 ortholog artifacts(同源基因制品)"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    query, subject = _copy_inputs_for_catalog(manifest, root)

    align_soft = manifest.options.align_soft or "last"
    dbtype = manifest.options.dbtype or "nucl"
    cscore = manifest.options.cscore if manifest.options.cscore is not None else 0.7
    dist = manifest.options.dist if manifest.options.dist is not None else 20

    with _blast_path_injected(manifest):
        command = run_python_step(
            "jcvi.compara.catalog.ortholog",
            jcvi_catalog.ortholog,
            [
                query,
                subject,
                f"--dbtype={dbtype}",
                f"--align_soft={align_soft}",
                "--full",
                "--no_strip_names",
                f"--cscore={cscore}",
                f"--dist={dist}",
                f"--min_size={max(1, manifest.options.min_block_size)}",
                f"--cpus={max(1, manifest.options.threads)}",
                "--no_dotplot",
            ],
            cwd=root,
        )
    _assert_ok(command)

    prefix = f"{query}.{subject}"
    reverse_prefix = f"{subject}.{query}"
    artifacts = {
        "blast_table": str(root / f"{prefix}.last"),
        "anchors": str(root / f"{prefix}.anchors"),
        "lifted_anchors": str(root / f"{prefix}.1x1.lifted.anchors"),
        "blocks": str(root / f"{prefix}.1x1.blocks"),
        "reverse_blocks": str(root / f"{reverse_prefix}.1x1.blocks"),
        "ortholog": str(root / f"{prefix}.ortholog"),
        "reverse_ortholog": str(root / f"{reverse_prefix}.ortholog"),
        "figures": [],
        "simplified_fallback": False,
        "backend": "jcvi.catalog.ortholog",
    }
    required = ["blast_table", "ortholog", "reverse_ortholog"]
    for key in required:
        path = Path(str(artifacts[key]))
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"JCVI catalog artifact was not created: {path}")
    return [command], artifacts
