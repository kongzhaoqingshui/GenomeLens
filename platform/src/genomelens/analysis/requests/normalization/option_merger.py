"""option_merger(选项合并器)：CLI、engine profile 与默认值的三方合并"""

# region import
from __future__ import annotations

import argparse
import os

from genomelens.data.config.config_models import ConfigModel
from genomelens.utils.parsers import parse_formats

# endregion


def _formats(args: argparse.Namespace, config: ConfigModel | None) -> list[str]:
    if str(args.formats).strip():
        return parse_formats(args.formats)

    # 运行时默认格式集中放在 runtime 组，避免 method config 重复维护同一来源
    if config:
        return parse_formats(config.runtime.default_formats)
    return ["svg"]


def _threads(args: argparse.Namespace, config: ConfigModel | None) -> int | None:
    if args.threads is not None:
        return int(args.threads)
    if config:
        return int(config.runtime.default_threads)

    # auto 工作流：默认把线程数限制在 1~8 之间
    return max(1, min(os.cpu_count() or 4, 8))


def _min_block_size(args: argparse.Namespace, config: ConfigModel | None) -> int | None:
    if args.min_block_size is not None:
        return int(args.min_block_size)
    if config:
        return int(config.profile.synteny.min_block_size)
    return None


def _log_level(args: argparse.Namespace, config: ConfigModel | None) -> str:
    value = str(getattr(args, "log_level", "") or "").strip().upper()
    if value:
        return value
    if bool(getattr(args, "verbose", False)):
        return "DEBUG"
    if config:
        return str(config.runtime.log_level or "INFO").upper()
    return "INFO"


def _align_soft(args: argparse.Namespace, config: ConfigModel | None) -> str:
    if str(args.align_soft).strip():
        return str(args.align_soft)
    if config:
        return config.profile.synteny.align_soft
    return "blast"


def _dbtype(args: argparse.Namespace, config: ConfigModel | None) -> str:
    if str(args.dbtype).strip():
        return str(args.dbtype)
    if config:
        return config.profile.synteny.dbtype
    return "nucl"


def _cscore(args: argparse.Namespace, config: ConfigModel | None) -> float:
    if args.cscore is not None:
        return float(args.cscore)
    if config:
        return float(config.profile.synteny.cscore)
    return 0.7


def _dist(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.dist is not None:
        return int(args.dist)
    if config:
        return int(config.profile.synteny.dist)
    return 20


def _iter(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.iter is not None:
        return int(args.iter)
    if config:
        return int(config.profile.synteny.iter)
    return 1


def _up(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.up is not None:
        return int(args.up)

    if config:
        return int(config.profile.local_synteny.up)
    return 20


def _down(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.down is not None:
        return int(args.down)

    if config:
        return int(config.profile.local_synteny.down)
    return 20


def _dpi(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.dpi is not None:
        return int(args.dpi)

    if config:
        return int(config.profile.plot.dpi)
    return 300


def _target_gene_ids(args: argparse.Namespace, config: ConfigModel | None) -> list[str]:
    """目标基因只能从 CLI 显式传入；V3 profile 不再承载任务身份"""

    text = str(args.target_genes).strip()
    if text:
        # CLI 入口使用逗号分隔字符串
        return [item.strip() for item in text.split(",") if item.strip()]
    return []


def _split_targets(args: argparse.Namespace, config: ConfigModel | None) -> bool:
    if args.split_targets:
        return True
    if config:
        return bool(config.profile.local_synteny.split_targets)
    return False


def _label_targets(args: argparse.Namespace, config: ConfigModel | None) -> bool:
    if args.label_targets:
        return True
    if config:
        return bool(config.profile.local_synteny.label_targets)
    return False


def _auto_optimization_flag(args: argparse.Namespace, config: ConfigModel | None, name: str) -> bool:
    if bool(getattr(args, name, False)):
        return True
    if config:
        return bool(getattr(config.profile.plot.auto_optimization, name, False))
    return False


def _auto_optimization_dict(args: argparse.Namespace, config: ConfigModel | None) -> dict[str, bool]:
    return {
        "optimize_figsize": _auto_optimization_flag(args, config, "optimize_figsize"),
        "rewrite_layout_links": _auto_optimization_flag(args, config, "rewrite_layout_links"),
        "optimize_karyotype_labels": _auto_optimization_flag(args, config, "optimize_karyotype_labels"),
    }


def _use_native_local_synteny_renderer(args: argparse.Namespace, config: ConfigModel | None) -> bool:
    if bool(getattr(args, "use_native_local_synteny_renderer", False)):
        return True
    if config:
        return bool(getattr(config.profile.local_synteny, "use_native_local_synteny_renderer", False))
    return False


def _style_arg(args: argparse.Namespace, config: ConfigModel | None, name: str) -> str:
    value = str(getattr(args, name, "") or "").strip()
    if value:
        return value

    # V3 样式参数统一归入 plot profile
    if config:
        return str(getattr(config.profile.plot, name, "") or "")
    return ""


def _string_arg(args: argparse.Namespace, name: str) -> str:
    return str(getattr(args, name, "") or "").strip()
