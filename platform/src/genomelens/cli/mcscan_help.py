"""Paged help for the mcscan CLI surface."""

from __future__ import annotations

from dataclasses import dataclass

from genomelens.cli.jcvi_subtasks import JCVI_SUBTASK_BY_NAME, JCVI_SUBTASKS, JcviSubtask
from genomelens.cli.ui import PALETTE, _paint, _supports_color


@dataclass(frozen=True)
class McscanHelpPage:
    """MCscan help 分页：key(页键)、title(标题)、summary(摘要) 与 arguments(参数列表)"""

    key: str
    title: str
    summary: str
    arguments: tuple[tuple[str, str], ...]


_PAGES: tuple[McscanHelpPage, ...] = (
    McscanHelpPage(
        "io",
        "输入输出",
        "输入目录、输出目录和配置文件路径。",
        (
            ("input_dir", "输入目录，自动发现同名物种文件对"),
            ("output_dir", "输出目录"),
            ("jcvi_config_positional", "可选 JCVI 配置文件路径，也可使用 --jcvi-config"),
            ("-c CONFIG, --config CONFIG", "GenomeLens 主配置 JSON 路径"),
            ("--jcvi-config JCVI_CONFIG", "JCVI 配置 JSON 路径，优先级高于位置参数"),
            ("--force", "允许复用已有输出目录"),
            ("-j, --json", "输出机器可读的原始 JSON 摘要"),
        ),
    ),
    McscanHelpPage(
        "species",
        "物种与参考",
        "选择参考物种，target_gene_ids 始终按参考物种解释。",
        (("--reference REFERENCE", "参考物种名称或 1-based 索引，默认第一个物种"),),
    ),
    McscanHelpPage(
        "runtime",
        "运行时与工具链",
        "运行线程和外部工具链路径。",
        (
            ("--threads THREADS", "线程数"),
            ("--jcvi-engine JCVI_ENGINE", "显式指定 jcvi-genomelens 引擎"),
            ("--blastn BLASTN", "显式指定 blastn 可执行文件"),
            ("--makeblastdb MAKEBLASTDB", "显式指定 makeblastdb 可执行文件"),
        ),
    ),
    McscanHelpPage(
        "homology",
        "同源搜索与共线性",
        "控制 BLAST/LAST/Diamond 和 MCscan block 过滤参数。",
        (
            ("--align-soft {blast,last,diamond_blastp}", "比对后端"),
            ("--dbtype {nucl,prot}", "序列类型：nucl 核酸 / prot 蛋白"),
            ("--cscore CSCORE", "同源匹配过滤强度，默认 0.7"),
            ("--dist DIST", "共线性锚点间最大基因距离，默认 20"),
            ("--iter ITER", "Block 过滤迭代次数，默认 1"),
            ("--min-block-size MIN_BLOCK_SIZE", "最小共线性 block 大小"),
        ),
    ),
    McscanHelpPage(
        "local",
        "目标基因局部共线性",
        "以参考物种中的目标基因为中心截取局部窗口。",
        (
            ("--target-genes TARGET_GENES", "目标基因 ID，多个用逗号分隔"),
            ("--up UP", "目标基因上游取多少个基因，默认 20"),
            ("--down DOWN", "目标基因下游取多少个基因，默认 20"),
            ("--split-targets", "多个目标基因时各自单独出图"),
            ("--label-targets", "在图中标注目标基因名称"),
            ("--use-native-local-synteny-renderer", "使用原生 matplotlib 渲染器（支持跨染色体窗口，计算较重）"),
        ),
    ),
    McscanHelpPage(
        "style",
        "图件样式",
        "控制输出格式和 JCVI 图件渲染样式。",
        (
            ("--formats FORMATS", "输出格式，例如 svg 或 svg,pdf"),
            ("--glyphstyle {box,arrow}", "基因形状"),
            ("--glyphcolor {orientation,orthogroup}", "基因着色"),
            ("--shadestyle {curve,line}", "连线样式"),
            ("--figsize FIGSIZE", "画布尺寸，例如 10x5"),
            ("--dpi DPI", "图片分辨率，默认 300"),
            ("--optimize-figsize", "自动推导 synteny 图件尺寸，默认关闭"),
            ("--rewrite-layout-links", "将跨轨道 layout 连线改写为链式连线，默认关闭"),
            ("--optimize-karyotype-labels", "自动优化全局核型图轨道标签位置，默认关闭"),
            ("--trim-cross-chromosome-blocks", "切除 blocks 中跨染色体的基因行，默认关闭"),
        ),
    ),
    McscanHelpPage(
        "histogram",
        "Histogram",
        "graphics_histogram 专用数值文件与绘图参数。",
        (
            ("--histogram-inputs HISTOGRAM_INPUTS", "附加数值文件，多个路径用逗号分隔"),
            ("--histogram-columns HISTOGRAM_COLUMNS", "0-based 列号列表，多个列用逗号分隔"),
            ("--histogram-skip HISTOGRAM_SKIP", "跳过输入文件前几行"),
            ("--histogram-bins HISTOGRAM_BINS", "直方图 bin 数"),
            ("--histogram-vmin HISTOGRAM_VMIN", "最小值下界，默认 0"),
            ("--histogram-vmax HISTOGRAM_VMAX", "最大值上界"),
            ("--histogram-xlabel HISTOGRAM_XLABEL", "X 轴标签"),
            ("--histogram-title HISTOGRAM_TITLE", "图标题"),
            ("--histogram-base {0,2,10}", "对数坐标底数，0 表示关闭"),
            ("--histogram-facet", "多序列时分面展示"),
            ("--histogram-fill HISTOGRAM_FILL", "柱体填充颜色"),
        ),
    ),
    McscanHelpPage(
        "diagnostics",
        "诊断开关",
        "低层 JCVI workflow 和诊断参数，通常不需要手动指定。",
        (
            ("--allow-simplified-fallback", "保留诊断开关，正式流程会拒绝简化降级"),
            ("--jcvi-workflow JCVI_WORKFLOW", "JCVI workflow 名称"),
            ("--jcvi-layout JCVI_LAYOUT", "JCVI layout 布局文件"),
            ("--jcvi-seqids JCVI_SEQIDS", "JCVI seqids 序列编号文件"),
        ),
    ),
)

_PAGE_BY_KEY = {page.key: page for page in _PAGES}


def _format_argument_rows(arguments: tuple[tuple[str, str], ...], *, enabled: bool) -> list[str]:
    width = max(len(name) for name, _description in arguments)
    rows: list[str] = []
    for name, description in arguments:
        name_cell = f"{name:<{width}}"
        rows.append(
            f"  {_paint(name_cell, PALETTE.cyan, enabled=enabled)}  "
            f"{_paint(description, PALETTE.gray, enabled=enabled)}"
        )
    return rows


def _render_index(*, jcvi: bool = False, enabled: bool) -> str:
    command = "genomelens analyze mcscan jcvi"
    page_prefix = "help analyze mcscan jcvi"
    title = "GenomeLens analyze mcscan jcvi" if jcvi else "GenomeLens analyze mcscan"
    lines = [
        _paint(title, PALETTE.bold + PALETTE.blue, enabled=enabled),
        "",
        f"{_paint('用法:', PALETTE.bold + PALETTE.blue, enabled=enabled)} "
        f"{_paint(command, PALETTE.cyan, enabled=enabled)} input_dir output_dir "
        "[jcvi_config_positional] [选项]",
        "",
        _paint(
            "这是 MCscan/JCVI 共线性分析入口。为避免长 help 淹没信息，参数按类别分页查看。",
            PALETTE.gray,
            enabled=enabled,
        ),
        "",
        _paint("常用:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        f"  {_paint(command, PALETTE.cyan, enabled=enabled)} .work/test/input .work/test/output "
        ".work/test/jcvi.config.json --force",
        f"  {_paint(command, PALETTE.cyan, enabled=enabled)} <input_dir> <output_dir> "
        "--reference subject --target-genes geneA",
        "",
        _paint("参数页:", PALETTE.bold + PALETTE.blue, enabled=enabled),
    ]
    for page in _PAGES:
        key = _paint(f"{page.key:<12}", PALETTE.cyan, enabled=enabled)
        title_text = _paint(page.title, PALETTE.yellow, enabled=enabled)
        summary = _paint(page.summary, PALETTE.gray, enabled=enabled)
        lines.append(f"  {key} {title_text} - {summary}")
    lines.extend(
        [
            "",
            _paint("子任务:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        ]
    )
    for subtask in JCVI_SUBTASKS:
        name = _paint(f"{subtask.name:<18}", PALETTE.cyan, enabled=enabled)
        title_text = _paint(subtask.title, PALETTE.yellow, enabled=enabled)
        summary = _paint(subtask.summary, PALETTE.gray, enabled=enabled)
        lines.append(f"  {name} {title_text} - {summary}")
    lines.extend(
        [
            "",
            _paint("查看:", PALETTE.bold + PALETTE.blue, enabled=enabled),
            f"  {_paint(page_prefix, PALETTE.cyan, enabled=enabled)} io",
            f"  {_paint(page_prefix, PALETTE.cyan, enabled=enabled)} local",
            f"  {_paint(page_prefix, PALETTE.cyan, enabled=enabled)} diagnostics",
            f"  {_paint(page_prefix, PALETTE.cyan, enabled=enabled)} graphics_dotplot",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_page(page: McscanHelpPage, *, enabled: bool) -> str:
    command = "genomelens analyze mcscan jcvi"
    prefix = "help analyze mcscan jcvi"
    lines = [
        f"{_paint(command, PALETTE.bold + PALETTE.blue, enabled=enabled)} - "
        f"{_paint(page.title, PALETTE.yellow, enabled=enabled)}",
        "",
        _paint(page.summary, PALETTE.gray, enabled=enabled),
        "",
        _paint("用法:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        f"  {_paint(command, PALETTE.cyan, enabled=enabled)} input_dir output_dir [jcvi_config_positional] [选项]",
        "",
        _paint("参数:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        *_format_argument_rows(page.arguments, enabled=enabled),
        "",
        _paint("其它页:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        f"  {_paint(prefix, PALETTE.cyan, enabled=enabled)} "
        + _paint(" | ".join(item.key for item in _PAGES if item.key != page.key), PALETTE.gray, enabled=enabled),
        "",
    ]
    return "\n".join(lines)


def _render_subtask(subtask: JcviSubtask, *, enabled: bool) -> str:
    command = f"genomelens analyze mcscan jcvi {subtask.name}"
    prefix = "help analyze mcscan jcvi"
    usage = (
        f"  {_paint(command, PALETTE.cyan, enabled=enabled)} number_file output_dir [jcvi_config_positional] [选项]"
        if subtask.name == "graphics_histogram"
        else f"  {_paint(command, PALETTE.cyan, enabled=enabled)} input_dir output_dir [jcvi_config_positional] [选项]"
    )
    example = (
        f"  {_paint(command, PALETTE.cyan, enabled=enabled)} numbers.txt outdir --histogram-columns 0,1 --force"
        if subtask.name == "graphics_histogram"
        else f"  {_paint(command, PALETTE.cyan, enabled=enabled)} <input_dir> <output_dir> --force"
    )
    lines = [
        f"{_paint(command, PALETTE.bold + PALETTE.blue, enabled=enabled)} - "
        f"{_paint(subtask.title, PALETTE.yellow, enabled=enabled)}",
        "",
        _paint(subtask.summary, PALETTE.gray, enabled=enabled),
        "",
        _paint("用法:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        usage,
        "",
        _paint("示例:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        example,
        "",
        _paint("共享参数页:", PALETTE.bold + PALETTE.blue, enabled=enabled),
        f"  {_paint(prefix, PALETTE.cyan, enabled=enabled)} "
        + _paint(" | ".join(item.key for item in _PAGES), PALETTE.gray, enabled=enabled),
        "",
    ]
    return "\n".join(lines)


def render_mcscan_help(path: list[str], *, color: bool | None = None) -> str | None:
    """Return custom mcscan help for `help analyze mcscan ...` paths."""

    if path[:2] != ["analyze", "mcscan"]:
        return None

    enabled = _supports_color() if color is None else color
    rest = path[2:]
    jcvi = bool(rest and rest[0] == "jcvi")
    if jcvi:
        rest = rest[1:]

    if not rest:
        return _render_index(jcvi=jcvi, enabled=enabled)

    if jcvi and rest[0] in JCVI_SUBTASK_BY_NAME:
        return _render_subtask(JCVI_SUBTASK_BY_NAME[rest[0]], enabled=enabled)

    page = _PAGE_BY_KEY.get(rest[0])
    if page is None:
        valid = ", ".join(
            ["jcvi", *[f"jcvi {item.key}" for item in _PAGES], *[f"jcvi {item.name}" for item in JCVI_SUBTASKS]]
        )
        return (
            f"{_paint('未知 mcscan help 页:', PALETTE.red, enabled=enabled)} {' '.join(path)}\n"
            f"{_paint('可用页:', PALETTE.bold + PALETTE.blue, enabled=enabled)} {valid}\n"
        )

    if not jcvi:
        valid = ", ".join(f"jcvi {item.key}" for item in _PAGES)
        return (
            f"{_paint('未知 mcscan help 页:', PALETTE.red, enabled=enabled)} {' '.join(path)}\n"
            f"{_paint('可用页:', PALETTE.bold + PALETTE.blue, enabled=enabled)} jcvi, {valid}\n"
        )

    return _render_page(page, enabled=enabled)
