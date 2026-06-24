import logging
from pathlib import Path

from genomelens.analysis.execution.resources.shared_runtime import build_shared_runtime_resources
from genomelens.analysis.planning.models import PairwiseArtifactInputs, SyntenyExecutionRequest
from genomelens.contracts.species import GenomeInputSpec, PreparedGenomeInputSpec, RawAnnotationInputSpec
from genomelens.data.workspace.output_layout import create_output_layout
from genomelens.toolchain.runtime.resource_locator import LocatedResource


def _raw_species(tmp_path: Path, name: str) -> GenomeInputSpec:
    gff = tmp_path / f"{name}.gff"
    genome = tmp_path / f"{name}.fa"
    gff.write_text("##gff-version 3\n", encoding="utf-8")
    genome.write_text(f">{name}\nATGC\n", encoding="utf-8")
    return GenomeInputSpec(name=name, raw=RawAnnotationInputSpec(gff=gff, genome=genome))


def _request(
    tmp_path: Path,
    reference: GenomeInputSpec,
    target: GenomeInputSpec,
    outdir: str,
) -> SyntenyExecutionRequest:
    return SyntenyExecutionRequest(reference=reference, target=target, outdir=tmp_path / outdir, force=True)


def test_build_plan_run_context_reuses_species_prepare_and_probe(monkeypatch, tmp_path: Path) -> None:
    species_a = _raw_species(tmp_path, "A")
    species_b = _raw_species(tmp_path, "B")
    species_c = _raw_species(tmp_path, "C")
    request_ab = _request(tmp_path, species_a, species_b, "pair-ab")
    request_ac = _request(tmp_path, species_a, species_c, "pair-ac")

    prepare_calls: list[str] = []
    resolve_calls: list[str] = []
    probe_calls: list[str] = []

    def fake_prepare_species_input(species: GenomeInputSpec, prepared_dir: Path):
        prepare_calls.append(species.name)
        bed = prepared_dir / f"{species.name}.bed"
        cds = prepared_dir / f"{species.name}.cds"
        bed.write_text("chr1\t0\t1\tgene1\n", encoding="utf-8")
        cds.write_text(f">{species.name}\nATGC\n", encoding="utf-8")
        return PreparedGenomeInputSpec(bed, cds), {"species": species.name}

    def fake_resolve_pairwise_toolchain(**_: object):
        resolve_calls.append("resolve")
        located = LocatedResource(name="tool", status="ok", path=str(tmp_path / "tool.exe"))
        return located, located, located, "", ""

    class FakeAdapter:
        def __init__(self, engine_path: str):
            self.engine_path = engine_path

        def probe(self) -> dict[str, object]:
            probe_calls.append(self.engine_path)
            return {"status": "ok", "engine_version": "1.0.0", "patchset": "test"}

    monkeypatch.setattr(
        "genomelens.analysis.execution.resources.shared_runtime.prepare_species_input",
        fake_prepare_species_input,
    )
    monkeypatch.setattr(
        "genomelens.analysis.execution.resources.shared_runtime.resolve_pairwise_toolchain",
        fake_resolve_pairwise_toolchain,
    )
    monkeypatch.setattr("genomelens.analysis.execution.resources.shared_runtime.JcviEngineAdapter", FakeAdapter)

    layout = create_output_layout(tmp_path / "out", force=True)
    context = build_shared_runtime_resources([request_ab, request_ac], layout, logging.getLogger("test"))

    assert prepare_calls.count("A") == 1
    assert sorted(prepare_calls) == ["A", "B", "C"]
    assert resolve_calls == ["resolve"]
    assert probe_calls == [str(tmp_path / "tool.exe")]
    assert context.species_cache_hits == 1
    assert context.species_cache_misses == 3


def test_shared_runtime_resolves_and_stores_pairwise_cache(monkeypatch, tmp_path: Path) -> None:
    species_a = _raw_species(tmp_path, "A")
    species_b = _raw_species(tmp_path, "B")
    request = _request(tmp_path, species_a, species_b, "pair-ab")

    def fake_prepare_species_input(species: GenomeInputSpec, prepared_dir: Path):
        bed = prepared_dir / f"{species.name}.bed"
        cds = prepared_dir / f"{species.name}.cds"
        bed.write_text("chr1\t0\t1\tgene1\n", encoding="utf-8")
        cds.write_text(f">{species.name}\nATGC\n", encoding="utf-8")
        return PreparedGenomeInputSpec(bed, cds), {"species": species.name}

    def fake_resolve_pairwise_toolchain(**_: object):
        located = LocatedResource(name="tool", status="ok", path=str(tmp_path / "tool.exe"))
        return located, located, located, "", ""

    class FakeAdapter:
        def __init__(self, engine_path: str):
            self.engine_path = engine_path

        def probe(self) -> dict[str, object]:
            return {"status": "ok", "engine_version": "1.0.0", "patchset": "test"}

    monkeypatch.setattr(
        "genomelens.analysis.execution.resources.shared_runtime.prepare_species_input",
        fake_prepare_species_input,
    )
    monkeypatch.setattr(
        "genomelens.analysis.execution.resources.shared_runtime.resolve_pairwise_toolchain",
        fake_resolve_pairwise_toolchain,
    )
    monkeypatch.setattr("genomelens.analysis.execution.resources.shared_runtime.JcviEngineAdapter", FakeAdapter)

    layout = create_output_layout(tmp_path / "out", force=True)
    context = build_shared_runtime_resources([request], layout, logging.getLogger("test"))

    anchors = tmp_path / "query.anchors"
    simple = tmp_path / "query.simple"
    blocks = tmp_path / "query.blocks"
    for artifact in (anchors, simple, blocks):
        artifact.write_text("data\n", encoding="utf-8")

    cache_key = context.store_pairwise_result(
        request,
        PairwiseArtifactInputs(anchors=anchors, simple=simple, blocks=blocks),
        logging.getLogger("test"),
    )
    decision = context.resolve_pairwise_request(request, logging.getLogger("test"))

    assert cache_key
    assert decision.cache_hit is True
    assert decision.cache_key == cache_key
    assert decision.request.precomputed_artifacts is not None
    assert decision.request.precomputed_artifacts.blocks is not None
    assert decision.request.precomputed_artifacts.blocks.is_file()
    assert decision.request.artifact_bundles[0].artifact_path("blocks") is not None
