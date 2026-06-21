"""Heavy-center entry for the gljcvimcscan HAIant package."""

from __future__ import annotations

import sys
from pathlib import Path

from genomelens_haiant_plugin import (
    PluginError,
    close_logging,
    discover_mcscan_home,
    genomelens_shell_path,
    load_params,
    resource_path,
    run_process,
    setup_logging,
    write_analysis_request,
)


def _build_center_command(params_path: str | Path) -> list[str]:
    params, base = load_params(params_path)
    logger = setup_logging(base, params.get("output_dir"))
    logger.info("Loaded params.json: %s", params_path)
    center_home = discover_mcscan_home(start=resource_path())
    shell = genomelens_shell_path(center_home)
    request_path = write_analysis_request(params, base, workflow="local_synteny")
    if shell.suffix.lower() in {".cmd", ".bat"}:
        argv = ["cmd.exe", "/c", str(shell), "analyze", "run", str(request_path)]
    else:
        argv = [str(shell), "analyze", "run", str(request_path)]
    logger.info("Dispatching GenomeLens shell: %s", argv)
    return argv


def build_center_command(params_path: str | Path) -> list[str]:
    """Build argv for the gljcvimcscan heavy-center entry."""

    try:
        return _build_center_command(params_path)
    finally:
        close_logging()


def main(argv: list[str] | None = None) -> int:
    """Run the gljcvimcscan heavy-center entry."""

    if argv is None:
        argv = sys.argv[1:]
    try:
        if len(argv) != 1:
            raise PluginError("Expected exactly one params.json path")
        return run_process(build_center_command(argv[0]))
    except PluginError as exc:
        print(f"gljcvimcscan error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
