from jcvi_genomelens.probe import build_probe_payload
from jcvi_genomelens.workflows.contract import SUPPORTED_WORKFLOWS


def test_probe_contract() -> None:
    payload = build_probe_payload()
    assert payload["engine_name"] == "jcvi-genomelens"
    assert payload["status"] == "ok"
    assert payload["runtime_mode"] in {"core", "accelerated"}
    assert isinstance(payload["loaded_extensions"], list)
    assert isinstance(payload["missing_extensions"], list)
    assert isinstance(payload["extension_errors"], dict)
    assert payload["capabilities"] == list(SUPPORTED_WORKFLOWS)
    assert payload["capabilities"] == [
        "mcscan_pairwise",
        "graphics_synteny",
        "graphics_dotplot",
        "graphics_histogram",
        "graphics_karyotype",
        "graphics_heatmap",
        "catalog_ortholog",
        "local_synteny",
        "graphics_karyotype_global",
        "local_synteny_multi",
    ]
    assert payload["dispatchable_workflows"] == payload["capabilities"]
    assert "submodule_to_workflow" not in payload
    assert "jcvi.graphics.dotplot" in payload["bundled_jcvi_modules"]
    assert "jcvi.graphics.heatmap" in payload["bundled_jcvi_modules"]
    assert "jcvi.graphics.histogram" in payload["bundled_jcvi_modules"]
    assert "jcvi.graphics.karyotype" in payload["bundled_jcvi_modules"]
