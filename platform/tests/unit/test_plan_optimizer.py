from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.models import WorkflowRequest, WorkflowSpeciesInput


def _species(name: str) -> WorkflowSpeciesInput:
    return WorkflowSpeciesInput(name=name, input_mode="bed_cds", bed=f"/tmp/{name}.bed", cds=f"/tmp/{name}.cds")


def _request(workflow_id: str, names: list[str]) -> WorkflowRequest:
    return WorkflowRequest.from_json(
        {
            "schema_version": 2,
            "kind": "workflow_request",
            "workflow_id": workflow_id,
            "species": [_species(name).to_json() for name in names],
            "reference_index": 0,
            "inputs": {},
            "parameters": {},
            "output": {"directory": "/tmp/out", "force": True, "formats": ["svg"]},
            "runtime": {},
        }
    )


def test_workflow_planner_exposes_raw_and_optimized_plan() -> None:
    request = _request("synteny", ["A", "B", "C"])

    planner = WorkflowPlanner()
    raw_plan = planner.build_raw_plan(request)
    optimized_plan = planner.build(request)

    assert raw_plan.optimizer_profile_id == ""
    assert raw_plan.shared_runtime_profile_id == ""
    assert optimized_plan.optimizer_profile_id == "synteny_pairwise_reuse_v1"
    assert optimized_plan.shared_runtime_profile_id == "pairwise_synteny_v1"
    assert optimized_plan.shared_runtime_step_kinds == ["pairwise_synteny"]


def test_single_pair_plan_keeps_optimizer_profile_without_shared_runtime() -> None:
    request = _request("synteny", ["A", "B"])

    plan = WorkflowPlanner().build(request)

    assert plan.optimizer_profile_id == "synteny_pairwise_reuse_v1"
    assert plan.shared_runtime_profile_id == ""
    assert plan.shared_runtime_step_kinds == []
