"""局部共线性 layout(布局) 审计工具"""

from __future__ import annotations

from jcvi_genomelens.graphics.local_synteny.models import LocalSyntenyLayout


def layout_audit(layout: LocalSyntenyLayout) -> dict[str, object]:
    """返回用于视觉回归检查的关键布局事实"""

    segments = [segment for track in layout.tracks for segment in track.segments]
    return {
        "track_count": len(layout.tracks),
        "segment_count": len(segments),
        "link_count": len(layout.links),
        "legend_entries": [entry.gene_id for entry in layout.target_legend_entries],
        "track_centers": {
            track.name: round(
                (
                    min(segment.visual_start for segment in track.segments)
                    + max(segment.visual_end for segment in track.segments)
                )
                / 2,
                6,
            )
            for track in layout.tracks
            if track.segments
        },
    }


__all__ = ["layout_audit"]
