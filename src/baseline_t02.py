"""Baseline for T02: Single global Laplacian variance threshold.

Cited from docs/tracks/T02.md:
"Baseline: Một ngưỡng Laplacian toàn ảnh duy nhất (src/common/image_ops.laplacian_variance), cùng testset & budget."
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image

from .common.contact_sheet import render_contact_sheet
from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.image_ops import laplacian_variance
from .common.manifest import verify_manifest
from .common.review import make_review_queue, write_review_queue
from .metrics.tracks import get_track


def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)
    manifest = ctx.input_dir / "manifest.csv"
    if manifest.exists():
        verify_manifest(manifest)

    images_df = pd.read_csv(ctx.input_dir / "images.csv")
    rows = []
    for _, r in images_df.iterrows():
        p = ctx.input_dir / r["path"]
        img = np.asarray(Image.open(p).convert("RGB"))
        sharp = laplacian_variance(img)
        # Single global inverted threshold: lower sharpness = higher defect score
        score = float(1.0 / (1.0 + sharp / 100.0))
        rows.append({
            "image_id": r["image_id"],
            "score": round(score, 4),
            "reason": f"laplacian_var={sharp:.1f}",
            "path": r["path"]
        })

    res = pd.DataFrame(rows)
    ctx.stats["n_items"] = len(res)
    budget = int(ctx.param("budget", 20))

    q = make_review_queue(res, id_col="image_id", score_col="score", budget=budget, reason_col="reason", evidence_col="path")
    write_review_queue(q, ctx.out("review_queue.csv"))

    render_contact_sheet(q, ctx.out("contact_sheet.html"), image_root=ctx.input_dir, title="T02 Laplacian Baseline Review Queue")

    out_file = ctx.out(spec.pred_file)
    res[["image_id", "score"]].to_csv(out_file, index=False)

    write_decision(
        Decision(
            status="HOLD",
            reason_code="BASELINE_ONLY",
            reason="Laplacian baseline: cannot release without multi-feature triage",
            owner=ctx.config.get("owner", "baseline"),
            scope=ctx.track,
            evidence=[str(out_file)]
        ),
        ctx.out("decision.json"),
        ctx.out("decision_log.csv")
    )
