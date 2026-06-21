"""Public API for the GenomeLens HAIant plugin adapter."""

from __future__ import annotations

from ._core import (
    GLJCVIMCSCAN_HOME_ENV,
    LOGGER_NAME,
    PLUGIN_RUNTIME_ENV,
    SUPPORTED_WORKFLOWS,
    PluginError,
    build_analysis_request,
    build_runtime_command,
    build_species_from_params,
    close_logging,
    discover_mcscan_home,
    genomelens_shell_path,
    load_params,
    main,
    parse_bool,
    plugin_root,
    resolve_param_path,
    resource_path,
    run_process,
    runtime_executable,
    setup_logging,
    write_analysis_request,
    write_runtime_request,
)

setup_adapter_logging = setup_logging
close_adapter_logging = close_logging

__all__ = [
    "GLJCVIMCSCAN_HOME_ENV",
    "LOGGER_NAME",
    "PLUGIN_RUNTIME_ENV",
    "SUPPORTED_WORKFLOWS",
    "PluginError",
    "build_analysis_request",
    "build_runtime_command",
    "build_species_from_params",
    "close_adapter_logging",
    "close_logging",
    "discover_mcscan_home",
    "genomelens_shell_path",
    "load_params",
    "main",
    "parse_bool",
    "plugin_root",
    "resolve_param_path",
    "resource_path",
    "run_process",
    "runtime_executable",
    "setup_adapter_logging",
    "setup_logging",
    "write_analysis_request",
    "write_runtime_request",
]
