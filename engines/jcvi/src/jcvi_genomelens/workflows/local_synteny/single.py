"""以目标基因为中心的局部共线性工作流

该工作流先运行一次 pairwise MCscan 得到全基因组 blocks，再按用户指定的
目标基因上下游窗口截取局部 blocks，最后调用 JCVI `graphics.synteny` 绘图。
当前版本支持一个参考物种（query）与一个目标物种（subject）。"""

# region import
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, cast

from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok, build_figure_options, close_matplotlib_figures
from jcvi_genomelens.workflows.graphics.plot_optimization import prepare_synteny_plot_inputs
from jcvi_genomelens.workflows.pairwise.artifact_reuse import ensure_pairwise_artifacts
from jcvi_genomelens.workflows.pairwise.mcscan import run as run_pairwise

# endregion

TARGET_BLOCK_HIGHLIGHT = "r"
_TRACK_LABEL_WRAP_THRESHOLD = 12
_TRACK_LABEL_ABBREVIATION_LIMIT = 18


def _display_track_label(label: str) -> str:
    """把默认轨道标签压缩成更适合图内显示的短文本"""

    normalized = re.sub(r"[_]+", " ", label.strip())
    normalized = re.sub(r"[- ]+(scaffold|chromosome)$", "", normalized, flags=re.IGNORECASE)
    parts = [part for part in re.split(r"[\s-]+", normalized) if part]
    if len(parts) >= 2:
        abbreviated = f"{parts[0][0]}. {parts[1]}"
        if (
            len(" ".join(parts[:2])) > _TRACK_LABEL_WRAP_THRESHOLD
            and len(abbreviated) <= _TRACK_LABEL_ABBREVIATION_LIMIT
        ):
            return abbreviated
    if len(normalized) <= _TRACK_LABEL_ABBREVIATION_LIMIT:
        return normalized
    return normalized[: _TRACK_LABEL_ABBREVIATION_LIMIT - 3] + "..."


def _layout_label_fields(label: str, default_va: str) -> tuple[str, str, str, int]:
    """为默认 layout 选择标签锚点、显示文本和字号"""

    display_label = _display_track_label(label)
    if len(display_label) > _TRACK_LABEL_WRAP_THRESHOLD:
        return "leftalign", "center", display_label, 9
    return "center", default_va, display_label, 10


def _read_bed_order(bed_path: Path) -> tuple[list[str], dict[str, int]]:
    """返回 BED 文件中 accn 的有序列表与下标映射"""

    order: list[str] = []
    seen: set[str] = set()
    with bed_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            accn = parts[3]
            if accn not in seen:
                seen.add(accn)
                order.append(accn)
    # BED 顺序就是局部窗口裁切时的“基因坐标轴”
    index = {accn: idx for idx, accn in enumerate(order)}
    return order, index


def _split_block_highlight(line: str) -> tuple[str | None, str]:
    """拆分 JCVI blocks 行首的 highlight 前缀"""

    if "*" not in line:
        return None, line
    highlight, body = line.split("*", 1)
    return highlight or None, body


def _mark_target_block_line(line: str, target_gene_ids: set[str]) -> str:
    """给目标基因所在的 blocks 行加 JCVI 红色 highlight 前缀"""

    _, body = _split_block_highlight(line)
    parts = body.split("\t")
    query_accn = parts[0].strip() if parts else ""
    if query_accn in target_gene_ids:
        return f"{TARGET_BLOCK_HIGHLIGHT}*{body}"
    return line


def _extract_local_blocks(
    blocks_path: Path,
    query_order: list[str],
    query_index: dict[str, int],
    target_gene_ids: list[str],
    up: int,
    down: int,
    split_targets: bool,
    query_label: str = "",
    subject_label: str = "",
) -> tuple[dict[str, list[str]], set[str]]:
    """从完整 blocks 中截取目标基因上下游窗口内的行

    返回：{target_key: 局部 blocks 行列表}, 被覆盖的 query 基因集合。
    """

    windows: list[tuple[str, int, int]] = []
    covered_genes: set[str] = set()
    for gene_id in target_gene_ids:
        idx = query_index.get(gene_id)
        if idx is None:
            continue
        start = max(0, idx - up)
        end = min(len(query_order) - 1, idx + down)
        windows.append((gene_id, start, end))
        for i in range(start, end + 1):
            covered_genes.add(query_order[i])

    if not windows:
        raise ValueError(
            f"目标基因 ID {target_gene_ids} 在参考物种的 BED 中未找到。"
            "请检查是否通过 --reference 或 config.mcscan.reference 指定了包含这些目标基因的参考物种。"
        )

    if not split_targets:
        # 取各目标窗口的“并集”而非“包络”：仅合并真正重叠/相邻的窗口，
        # 彼此相距很远的目标各自保留独立窗口，避免它们之间数百个无关基因
        # 被一并纳入（旧实现用 [min_start, max_end] 包络，远距离目标会撑出
        # 上千行 block）。所有子窗口共用同一个 key，仍输出为一张合并图。
        merged_key = windows[0][0] if len(windows) == 1 else "merged"
        intervals = sorted((start, end) for _, start, end in windows)
        union: list[tuple[int, int]] = []
        for start, end in intervals:
            if union and start <= union[-1][1] + 1:
                union[-1] = (union[-1][0], max(union[-1][1], end))
            else:
                union.append((start, end))
        windows = [(merged_key, start, end) for start, end in union]
        covered_genes = set()
        for _, start, end in windows:
            for i in range(start, end + 1):
                covered_genes.add(query_order[i])

    local_blocks: dict[str, list[str]] = {key: [] for key, _, _ in windows}
    if not blocks_path.is_file():
        return local_blocks, covered_genes

    def _has_subject(parts: list[str]) -> bool:
        return any(accn.strip() and accn.strip() != "." for accn in parts[1:])

    target_gene_set = set(target_gene_ids)
    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if not line or line.startswith("#"):
                continue
            _, block_body = _split_block_highlight(line)
            parts = block_body.split("\t")
            if len(parts) < 2:
                continue
            query_accn = parts[0].strip()
            if not _has_subject(parts):
                continue
            for key, start, end in windows:
                idx = query_index.get(query_accn)
                if idx is not None and start <= idx <= end:
                    local_blocks[key].append(_mark_target_block_line(line, target_gene_set))
                    break

    for key, lines in local_blocks.items():
        if not lines:
            target_label = key if key != "merged" else ", ".join(target_gene_ids)
            raise ValueError(
                f"在参考物种 '{query_label}' 的目标基因窗口内未找到与目标物种 "
                f"'{subject_label}' 的同源区块：{target_label}。"
                "请检查 --reference / config.mcscan.reference 是否指向包含目标基因的参考物种。"
            )
    return local_blocks, covered_genes


def _write_local_layout(
    path: Path,
    query_label: str,
    subject_label: str,
) -> Path:
    """写出以参考物种为中心的局部共线性双轨 layout"""

    query_ha, query_va, query_display, query_fontsize = _layout_label_fields(query_label, "top")
    subject_ha, subject_va, subject_display, subject_fontsize = _layout_label_fields(subject_label, "bottom")
    path.write_text(
        "\n".join(
            [
                "# x, y, rotation, ha, va, color, ratio, label",
                "0.50, 0.65, 0, {query_ha}, {query_va}, #2f6f73, 1, {query}, {query_fontsize}",
                "0.50, 0.35, 0, {subject_ha}, {subject_va}, #b85c38, 1, {subject}, {subject_fontsize}",
                "e, 0, 1, #c8c8c8",
            ]
        ).format(
            query_ha=query_ha,
            query_va=query_va,
            query=query_display,
            query_fontsize=query_fontsize,
            subject_ha=subject_ha,
            subject_va=subject_va,
            subject=subject_display,
            subject_fontsize=subject_fontsize,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行目标基因局部共线性分析

    步骤：
    1. 运行 pairwise MCscan 得到全基因组 blocks。
    2. 按目标基因上下游窗口截取局部 blocks。
    3. 生成局部 layout。
    4. 调用 JCVI graphics.synteny 或自实现渲染器出图。
    """

    from jcvi.graphics.synteny import main as jcvi_graphics_synteny
    from jcvi_genomelens.graphics.local_synteny import render_local_synteny

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)

    if manifest.query is None or manifest.subject is None:
        raise ValueError("local_synteny requires query and subject species")

    target_gene_ids = manifest.options.target_gene_ids
    if not target_gene_ids:
        raise ValueError("local_synteny workflow requires target_gene_ids")

    use_native = manifest.options.use_native_local_synteny_renderer

    # local_synteny 的上游依赖就是完整 pairwise 结果，局部图只是在 blocks 上二次裁切
    commands, pairwise_artifacts = ensure_pairwise_artifacts(
        manifest,
        root,
        required_fields=("blocks",),
        ensure_merged_bed=True,
        fallback_runner=run_pairwise,
    )
    blocks_path = Path(str(pairwise_artifacts["blocks"]))
    merged_bed = Path(str(pairwise_artifacts["merged_bed"]))
    query_bed = manifest.query.bed

    query_order, query_index = _read_bed_order(query_bed)
    local_blocks_map, _ = _extract_local_blocks(
        blocks_path,
        query_order,
        query_index,
        target_gene_ids,
        up=max(1, manifest.options.up),
        down=max(1, manifest.options.down),
        split_targets=manifest.options.split_targets,
        query_label=manifest.query.name,
        subject_label=manifest.subject.name,
    )

    formats = manifest.options.formats or ["svg"]
    # 局部图单独落到 sibling `local/` 目录，避免与全局 pairwise 产物混在一起
    local_dir = root.parent / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    local_figures: list[str] = []
    local_artifacts: list[dict[str, object]] = []

    plot_options = {
        "figsize": manifest.options.figsize,
        "dpi": manifest.options.dpi,
        "glyphstyle": manifest.options.glyphstyle,
        "glyphcolor": manifest.options.glyphcolor,
        "shadestyle": manifest.options.shadestyle,
        "label_targets": manifest.options.label_targets,
        "target_gene_ids": manifest.options.target_gene_ids,
    }

    for key, lines in local_blocks_map.items():
        local_blocks = local_dir / f"{key}.local.blocks"
        local_layout = local_dir / f"{key}.local.layout"
        local_bed = local_dir / f"{key}.local.bed"

        # 每个 target/window 都生成自己的 blocks/layout/bed，方便后续单独复检
        local_blocks.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        shutil.copy2(merged_bed, local_bed)
        _write_local_layout(local_layout, manifest.query.name, manifest.subject.name)
        plot_inputs = prepare_synteny_plot_inputs(
            blocks=local_blocks,
            bed=local_bed,
            layout=local_layout,
            root=local_dir,
            stem=f"{key}.local.optimized",
            options=manifest.options,
        )

        for fmt in formats:
            output_prefix = local_dir / f"{key}.local"
            figure = Path(f"{output_prefix}.{fmt}")

            if use_native:
                # 使用原生 matplotlib 渲染器以支持跨染色体绘制
                argv = [
                    str(plot_inputs.blocks),
                    str(plot_inputs.bed),
                    str(figure),
                    "--track-names",
                    manifest.query.name,
                    manifest.subject.name,
                    "--target-gene-ids",
                    *target_gene_ids,
                ]
                if plot_inputs.figsize:
                    argv.extend(["--figsize", plot_inputs.figsize])
                close_matplotlib_figures()
                try:
                    render_local_synteny(
                        blocks_path=plot_inputs.blocks,
                        bed_path=plot_inputs.bed,
                        output_path=figure,
                        track_names=[manifest.query.name, manifest.subject.name],
                        target_gene_ids=list(target_gene_ids),
                        label_targets=bool(plot_options.get("label_targets")),
                        figsize=plot_inputs.figsize,
                        dpi=manifest.options.dpi,
                        fmt=fmt,
                    )
                finally:
                    close_matplotlib_figures()
                command = CommandAudit(
                    name="local_synteny_renderer",
                    argv=argv,
                    returncode=0,
                    cwd=str(root),
                )
            else:
                figure_args = build_figure_options(manifest.options, fmt, plot_inputs.figsize)
                if manifest.options.label_targets and target_gene_ids:
                    figure_args.extend(["--genelabels", ",".join(target_gene_ids)])
                close_matplotlib_figures()
                try:
                    command = run_python_step(
                        "jcvi.graphics.synteny",
                        jcvi_graphics_synteny,
                        [
                            str(plot_inputs.blocks),
                            str(plot_inputs.bed),
                            str(plot_inputs.layout),
                            *figure_args,
                            "--outputprefix",
                            str(output_prefix),
                        ],
                        cwd=root,
                    )
                finally:
                    close_matplotlib_figures()

            commands.append(command)
            _assert_ok(command)
            if not figure.is_file() or figure.stat().st_size == 0:
                raise RuntimeError(f"Local synteny figure was not created: {figure}")
            local_figures.append(str(figure))

        local_artifacts.append(
            {
                "target": key,
                "blocks": str(local_blocks),
                "bed": str(local_bed),
                "layout": str(local_layout),
                "plot_optimization": plot_inputs.artifacts,
                "figures": [str(local_dir / f"{key}.local.{fmt}") for fmt in formats],
            }
        )

    artifacts = {
        **pairwise_artifacts,
        "local_figures": local_figures,
        "local_artifacts": local_artifacts,
        "figures": cast(list[Any], pairwise_artifacts.get("figures") or []) + local_figures,
    }
    return commands, artifacts
