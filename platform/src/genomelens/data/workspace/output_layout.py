"""一次 GenomeLens 运行的标准输出布局"""

# region import
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# endregion


@dataclass(frozen=True)
class OutputLayout:
    """OutputLayout(输出布局)：命名所有稳定目录和文件"""

    # fmt: off
    root: Path                   # 输出根目录
    inputs: Path                 # 用户输入拷贝目录
    prepared: Path               # 预处理后的输入目录
    intermediate: Path           # 中间产物根目录
    blast: Path                  # BLAST 相关中间文件目录
    cache: Path                  # 缓存目录
    jcvi: Path                   # JCVI 引擎工作目录
    ortholog: Path               # 同源基因分析中间目录
    mcscan: Path                 # MCscan 中间目录
    local: Path                  # 局部共线性中间目录
    logs: Path                   # 日志目录
    report: Path                 # 报告目录
    results: Path                # 最终结果根目录
    figures: Path                # 图件输出目录
    manifest: Path               # 引擎运行清单文件路径
    engine_summary: Path         # 引擎 summary JSON 路径
    run_summary: Path            # 运行总摘要 JSON 路径
    preprocessing_summary: Path  # 预处理摘要 JSON 路径
    # fmt: on


def build_output_layout(outdir: str | Path) -> OutputLayout:
    """创建标准输出布局对象，不触碰文件系统"""

    root = Path(outdir).expanduser().resolve(strict=False)
    inputs = root / "inputs"
    prepared = inputs / "prepared"
    intermediate = root / "intermediate"
    # 这里先只声明稳定路径，不做 mkdir，方便 dry-run/测试直接断言布局
    jcvi = intermediate / "jcvi"
    ortholog = intermediate / "ortholog"
    mcscan = intermediate / "mcscan"
    local = intermediate / "local"
    return OutputLayout(
        root=root,
        inputs=inputs,
        prepared=prepared,
        intermediate=intermediate,
        blast=intermediate / "blast",
        cache=intermediate / "cache",
        jcvi=jcvi,
        ortholog=ortholog,
        mcscan=mcscan,
        local=local,
        logs=root / "logs",
        report=root / "report",
        results=root / "results",
        figures=root / "results" / "figures",
        manifest=jcvi / "jcvi_engine_manifest.json",
        engine_summary=jcvi / "engine_run_summary.json",
        run_summary=root / "report" / "run_summary.json",
        preprocessing_summary=prepared / "preprocessing_summary.json",
    )


def create_output_layout(outdir: str | Path, *, force: bool = False) -> OutputLayout:
    """为一次运行创建目录，并保护已有的非空输出目录"""

    layout = build_output_layout(outdir)
    # 非空 outdir 默认视为危险复用，只有明确 --force 才允许继续写入
    if layout.root.exists() and any(layout.root.iterdir()) and not force:
        from genomelens.app.errors.exceptions import WorkspaceError

        raise WorkspaceError(f"Output directory is not empty. Use --force to reuse: {layout.root}")
    for directory in [
        layout.inputs,
        layout.prepared,
        layout.jcvi,
        layout.logs,
        layout.report,
        layout.figures,
    ]:
        # 只创建稳定目录；具体产物文件由对应阶段按需写入
        directory.mkdir(parents=True, exist_ok=True)
    # blast/cache/jcvi 子目录（ortholog/mcscan/local/blast/cache）按需创建，
    # 避免空目录 clutter
    return layout
