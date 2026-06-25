"""WorkflowDispatcher：把 WorkflowRequest 展开为执行计划并运行"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from genomelens.analysis.execution.executor import PlanExecutor
from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.requests.normalizer import normalize_analysis_request
from genomelens.analysis.requests.task_loader import write_task_request
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary

# endregion


class WorkflowDispatcher:
    """WorkflowDispatcher：只处理 synteny 一站式 WorkflowRequest"""

    def dispatch(self, request: WorkflowRequest, signal_bus: SignalBus | None = None) -> RunSummary:
        """运行一个 WorkflowRequest"""

        normalized = normalize_analysis_request(request)
        plan = WorkflowPlanner().build(normalized)
        summary = PlanExecutor().execute(plan, signal_bus or SignalBus())
        if isinstance(summary, dict):
            summary = RunSummary.from_json(summary)

        self._write_request_snapshot(normalized, summary)
        return summary

    def _write_request_snapshot(self, request: WorkflowRequest, summary: RunSummary) -> None:
        """写出实际执行请求快照并回填 run_summary"""

        outdir = Path(request.output.directory).expanduser().resolve(strict=False)
        request_path = write_task_request(request, outdir / "inputs" / "workflow_request.json")
        data = summary.to_json()
        data["analysis_request_path"] = str(request_path)

        run_summary_path = outdir / "report" / "run_summary.json"
        if run_summary_path.is_file():
            run_summary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
