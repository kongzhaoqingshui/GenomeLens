"""外部 jcvi-genomelens engine adapter(引擎适配器)

模块职责：
- probe(探测) engine(引擎)
- 写出 manifest(跨层协议)
- 调用 engine run(引擎运行)
- 解析 `engine_run_summary.json`
"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from genomelens.app.errors.exceptions import EngineProbeError, EngineRunError, SummaryParseError
from genomelens.engines.jcvi.models import JcviRunResult
from genomelens.toolchain.runtime.subprocess_runner import run_command
from genomelens.utils.constants import ENGINE_RUN_TIMEOUT_SECONDS, PROBE_TIMEOUT_SECONDS

# endregion


class JcviEngineAdapter:
    """JcviEngineAdapter(engine 适配器)：唯一合法的 shell-to-engine(外壳到引擎) 门面"""

    def __init__(self, engine_path: str | Path):
        self.engine_path = str(engine_path)

    def probe(self) -> dict[str, object]:
        """运行 engine probe(引擎探测) 并解析 JSON 输出"""

        result = run_command([self.engine_path, "probe", "--json"], timeout=PROBE_TIMEOUT_SECONDS)
        if not result.ok:
            raise EngineProbeError(result.stderr or result.stdout or f"probe failed: {result.returncode}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise EngineProbeError(f"probe did not return JSON: {result.stdout}") from exc
        if payload.get("status") != "ok":
            raise EngineProbeError(f"engine probe status is not ok: {payload}")
        return payload

    def write_manifest(self, manifest: dict[str, object], path: str | Path) -> Path:
        """用 UTF-8 编码写出 manifest JSON(清单 JSON)"""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def run_manifest(self, manifest_path: str | Path, outdir: str | Path) -> JcviRunResult:
        """用 manifest(清单) 运行 engine(引擎)，并解析摘要"""

        result = run_command(
            [self.engine_path, "run", "--manifest", manifest_path, "--outdir", outdir],
            timeout=ENGINE_RUN_TIMEOUT_SECONDS,
        )
        summary_path = Path(outdir) / "engine_run_summary.json"
        if not result.ok:
            if summary_path.is_file():
                parsed = self.parse_engine_summary(summary_path)
                raise EngineRunError(f"engine failed with summary: {parsed.error}")
            raise EngineRunError(result.stderr or result.stdout or f"engine run failed: {result.returncode}")
        return self.parse_engine_summary(summary_path)

    def parse_engine_summary(self, summary_path: str | Path) -> JcviRunResult:
        """解析公开 engine summary(引擎摘要) 契约"""

        path = Path(summary_path)
        if not path.is_file():
            raise SummaryParseError(f"engine summary not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SummaryParseError(f"engine summary is not valid JSON: {path}") from exc

        artifacts = payload.get("artifacts") or {}
        if not isinstance(artifacts, dict):
            raise SummaryParseError("engine summary artifacts must be an object")
        return JcviRunResult(
            status=str(payload.get("status") or "failed"),
            summary_path=path,
            engine_version=str(payload.get("engine_version") or ""),
            jcvi_upstream_version=str(payload.get("jcvi_upstream_version") or ""),
            patchset=str(payload.get("patchset") or ""),
            artifacts=artifacts,
            distribution=str(payload.get("distribution") or ""),
            runtime_mode=str(payload.get("runtime_mode") or ""),
            loaded_extensions=list(payload.get("loaded_extensions") or []),
            missing_extensions=list(payload.get("missing_extensions") or []),
            task=dict(payload.get("task") or {}),
            species=list(payload.get("species") or []),
            artifact_index=list(payload.get("artifact_index") or []),
            error=payload.get("error"),
        )
