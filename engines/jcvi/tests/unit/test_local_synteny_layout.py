from pathlib import Path

from jcvi_genomelens.manifest_models import EngineRunManifest, EngineTrack, ToolchainSpec, WorkflowOptions
from jcvi_genomelens.workflows.local_synteny import _write_local_layout
from jcvi_genomelens.workflows.local_synteny_multi import _write_multi_local_layout


def test_write_local_layout_compacts_long_track_label(tmp_path: Path) -> None:
    layout = tmp_path / "local.layout"

    _write_local_layout(layout, "Eutrema_salsugineum-Scaffold", "Iin.Chr")

    lines = layout.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "0.50, 0.65, 0, leftalign, center, #2f6f73, 1, E. salsugineum, 9"
    assert lines[2] == "0.50, 0.35, 0, center, bottom, #b85c38, 1, Iin.Chr, 10"


def test_write_multi_local_layout_compacts_long_track_label(tmp_path: Path) -> None:
    bed = tmp_path / "track.bed"
    bed.write_text("chr1\t0\t10\tgene1\t0\t+\n", encoding="utf-8")
    manifest = EngineRunManifest(
        workflow="local_synteny_multi",
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
        tracks=[
            EngineTrack("Eutrema_salsugineum-Scaffold", bed),
            EngineTrack("Iin.Chr", bed),
            EngineTrack("TAIR10", bed),
        ],
        blocks=tmp_path / "local.blocks",
        bed=bed,
    )
    layout = tmp_path / "local_multi.layout"

    _write_multi_local_layout(layout, manifest)

    lines = layout.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "0.50, 0.8200, 0, leftalign, center, #2f6f73, 1, E. salsugineum, 9"
    assert lines[2] == "0.50, 0.5000, 0, center, bottom, #b85c38, 1, Iin.Chr, 10"
    assert lines[3] == "0.50, 0.1800, 0, center, bottom, #5b8c5a, 1, TAIR10, 10"
