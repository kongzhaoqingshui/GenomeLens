"""独立图形命令：封装非共线性类的 JCVI 绘图 workflow"""

# region import
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from genomelens.app.controller.runners._shared import build_run_summary, scoring_placeholder, ui_block
from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import InputValidationError, ToolchainError
from genomelens.cli.ui import ConsoleWriter, render_analysis_summary
from genomelens.core.jcvi_adapter.adapter import JcviEngineAdapter
from genomelens.core.jcvi_adapter.adapter_models import HeatmapPlotRequest, JcviRunResult
from genomelens.core.models import ArtifactRecord
from genomelens.core.summary_models import RunSummary
from genomelens.core.visualization.figure_archiver import archive_figures
from genomelens.data.config.config_store import read_optional_config
from genomelens.data.logging.log_setup import run_with_logging
from genomelens.data.logging.task_log import task_scope
from genomelens.data.workspace.output_layout import build_output_layout, create_output_layout
from genomelens.toolchain.runtime.resource_locator import locate_engine
from genomelens.utils.parsers import parse_formats

# endregion


_CONSOLE = ConsoleWriter()


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 `plot` 顶层命令树"""

    parser = subparsers.add_parser("plot", help="Run standalone plotting workflows")
    nested = parser.add_subparsers(dest="plot_command", required=True)

    heatmap_parser = nested.add_parser("heatmap", help="Render a JCVI heatmap from matrix CSV")
    heatmap_parser.add_argument("matrix_csv", help="矩阵 CSV 文件路径")
    heatmap_parser.add_argument("output_dir", help="输出目录")
    heatmap_parser.add_argument("-c", "--config", default="", help="GenomeLens 主配置 JSON 路径")
    heatmap_parser.add_argument("--jcvi-config", default="", help="JCVI 配置 JSON 路径")
    heatmap_parser.add_argument("--jcvi-engine", default="", help="显式指定 jcvi-genomelens 引擎")
    heatmap_parser.add_argument("--formats", default="", help="输出格式，例如 png 或 svg,pdf")
    heatmap_parser.add_argument("--figsize", default="", help="画布尺寸，例如 8x8")
    heatmap_parser.add_argument("--dpi", type=int, default=None, help="图片分辨率，默认 300")
    heatmap_parser.add_argument("--cmap", default="", help="matplotlib colormap 名称，默认 jet")
    heatmap_parser.add_argument("--groups", action="store_true", help="CSV 首行包含列分组信息")
    heatmap_parser.add_argument("--rowgroups", default="", help="可选：行分组文件路径")
    heatmap_parser.add_argument("--horizontalbar", action="store_true", help="改用水平色条")
    heatmap_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="")
    heatmap_parser.add_argument("--force", action="store_true", help="允许复用已有输出目录")
    heatmap_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读的原始 JSON 摘要")
    heatmap_parser.set_defaults(func=run_heatmap)


def _artifact_record(
    artifact_id: str,
    artifact_type: str,
    path: str | Path,
    *,
    produced_by: str,
    preview: bool = False,
) -> dict[str, object]:
    """构造单个 artifact(产物) 记录"""

    text = str(path)
    return ArtifactRecord(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        path=text,
        produced_by=produced_by,
        format=Path(text).suffix.lower().lstrip("."),
        preview=preview,
    ).to_json()


def _build_artifact_index(
    workflow: str,
    layout_manifest: Path,
    engine_result: JcviRunResult,
    run_log: Path,
    final_figures: list[str],
) -> list[dict[str, object]]:
    """为热图结果构建 artifact 索引"""

    records = [
        _artifact_record("input_manifest", "manifest", layout_manifest, produced_by=workflow),
        _artifact_record("engine_summary", "summary", engine_result.summary_path, produced_by=workflow),
        _artifact_record("run_log", "log", run_log, produced_by=workflow),
    ]

    matrix = engine_result.artifacts.get("matrix")
    if matrix:
        records.append(_artifact_record("matrix", "matrix", str(matrix), produced_by=workflow))
    rowgroups = engine_result.artifacts.get("rowgroups")
    if rowgroups:
        records.append(_artifact_record("rowgroups", "rowgroups", str(rowgroups), produced_by=workflow))

    for index, figure in enumerate(final_figures, start=1):
        records.append(_artifact_record(f"figure_{index}", "figure", figure, produced_by=workflow, preview=True))
    return records


def _build_run_summary(
    layout_root: Path,
    workflow: str,
    engine_result: JcviRunResult,
    manifest: dict[str, object],
    final_figures: list[str],
) -> RunSummary:
    """构造独立热图命令的 RunSummary"""

    layout = build_output_layout(layout_root)
    run_log = layout.logs / "run.log"
    task = engine_result.task or cast(dict[str, object], manifest.get("task") or {})
    status = "SUCCEEDED" if engine_result.status == "ok" else "FAILED"
    return build_run_summary(
        status=status,
        workflow=workflow,
        method="plot",
        task=task,
        species=[],
        final_figures=final_figures,
        artifact_index=_build_artifact_index(workflow, layout.manifest, engine_result, run_log, final_figures),
        logs={
            "run_log": str(run_log),
            "run_summary": str(layout.run_summary),
        },
        ui=ui_block(
            status,
            final_figures,
            summary_path=layout.run_summary,
            log_path=run_log,
        ),
        scoring=scoring_placeholder(),
        method_data={
            "backend": str(engine_result.artifacts.get("backend") or ""),
            "heatmap_cmap": str(engine_result.artifacts.get("heatmap_cmap") or ""),
            "heatmap_groups": bool(engine_result.artifacts.get("heatmap_groups", False)),
            "heatmap_horizontalbar": bool(engine_result.artifacts.get("heatmap_horizontalbar", False)),
            "engine_summary_path": str(engine_result.summary_path),
        },
    )


def _print_summary(summary: RunSummary, *, json_output: bool) -> int:
    """输出热图命令摘要"""

    writer = ConsoleWriter(json_mode=json_output)
    if json_output:
        writer.print_json(summary.to_json())
    else:
        writer.print_text(render_analysis_summary(summary))
    return 0 if summary.status == "SUCCEEDED" else 7


def run_heatmap(args: argparse.Namespace) -> int:
    """运行独立 `graphics_heatmap` 工作流"""

    matrix = Path(args.matrix_csv).expanduser().resolve(strict=False)
    if not matrix.is_file():
        raise InputValidationError(f"矩阵 CSV 不存在：{matrix}")

    rowgroups = Path(args.rowgroups).expanduser().resolve(strict=False) if str(args.rowgroups).strip() else None
    if rowgroups is not None and not rowgroups.is_file():
        raise InputValidationError(f"行分组文件不存在：{rowgroups}")

    config = read_optional_config(args.config, jcvi_config_path=args.jcvi_config)
    engine = locate_engine(explicit=str(args.jcvi_engine or ""), config=config)
    if not engine.ok:
        raise ToolchainError(messages.TOOLCHAIN_ENGINE_NOT_FOUND.format(message=engine.message))

    default_formats = config.runtime.default_formats if config is not None else ["svg"]
    formats = parse_formats(args.formats) if str(args.formats).strip() else list(default_formats)
    request = HeatmapPlotRequest(
        matrix=matrix,
        outdir=Path(args.output_dir).expanduser().resolve(strict=False),
        formats=formats,
        jcvi_engine=engine.path,
        figsize=str(args.figsize or "").strip(),
        dpi=int(args.dpi if args.dpi is not None else 300),
        cmap=str(args.cmap or "").strip(),
        groups=bool(args.groups),
        rowgroups=rowgroups,
        horizontalbar=bool(args.horizontalbar),
        force=bool(args.force),
        log_level=str(args.log_level or (config.runtime.log_level if config is not None else "INFO")).upper(),
    )

    layout = build_output_layout(request.outdir)
    create_output_layout(request.outdir, force=request.force)
    with run_with_logging(
        layout.logs / "run.log",
        level=request.log_level,
        console=False,
        concise=True,
    ) as logger:
        adapter = JcviEngineAdapter(request.jcvi_engine)
        with task_scope(logger, task_id=request.task_id, step="probe_engine", context={"engine": request.jcvi_engine}):
            adapter.probe()

        with task_scope(
            logger,
            task_id=request.task_id,
            step="write_manifest",
            context={"manifest": str(layout.manifest)},
        ):
            manifest = adapter.build_heatmap_manifest(request)
            adapter.write_manifest(manifest, layout.manifest)
            layout.inputs.mkdir(parents=True, exist_ok=True)
            (layout.inputs / "input_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        with task_scope(
            logger,
            task_id=request.task_id,
            step="run_engine",
            context={"engine_outdir": str(layout.jcvi)},
        ):
            engine_result = adapter.run_manifest(layout.manifest, layout.jcvi)

        with task_scope(logger, task_id=request.task_id, step="archive_figures"):
            figures = [str(item) for item in cast(list[object], engine_result.artifacts.get("figures") or [])]
            final_figures = archive_figures(figures, layout.figures)

        with task_scope(logger, task_id=request.task_id, step="write_summary"):
            summary = _build_run_summary(request.outdir, request.workflow, engine_result, manifest, final_figures)
            layout.run_summary.write_text(
                json.dumps(summary.to_json(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    return _print_summary(summary, json_output=bool(args.json))
