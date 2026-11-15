"""Unit and regression tests for Group G07 T02 Pipeline.

Requirements: >= 2 tests (success + failure/edge), 0 failed.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import pytest

from src.common.context import RunContext
from src.common.decision import Decision
from src.pipeline import _score_image, decide, process


@pytest.fixture
def sample_context(tmp_path: Path) -> RunContext:
    cfg = {
        "group_id": "G07",
        "owner": "Hoang Ba Dat (2A202603100)",
        "track": "t02",
        "seed": 42,
        "offline": True,
        "params": {"budget": 20}
    }
    in_dir = Path("fixtures/t02_raw_qc")
    return RunContext(
        track="t02",
        input_dir=in_dir,
        output_dir=tmp_path,
        config=cfg,
        seed=42,
        rng=np.random.default_rng(42)
    )


def test_t02_pipeline_success(sample_context: RunContext):
    """Test standard execution of process(): correct columns, scores in [0, 1]."""
    images_df = pd.read_csv(sample_context.input_dir / "images.csv").head(10)
    data = {"images": images_df}

    result = process(sample_context, data)

    # Check required columns
    assert "image_id" in result.columns
    assert "score" in result.columns
    assert "pred_defect_type" in result.columns
    assert "pred_action" in result.columns

    # Check score bounds
    assert (result["score"] >= 0.0).all()
    assert (result["score"] <= 1.0).all()

    # Check valid actions
    assert set(result["pred_action"].unique()).issubset({"KEEP", "RECAPTURE"})


def test_t02_pipeline_edge_cases(sample_context: RunContext):
    """Failure mode tests:

    1. Clean night images must NOT be falsely classified as dark defect.
    2. Softer camera (cam_B) clean images must NOT be falsely classified as blur defect.
    """
    images_df = pd.read_csv(sample_context.input_dir / "images.csv")

    # Find a clean night image (e.g., img_01_0 or img_01_1)
    clean_night = images_df[(images_df.light == "night") & (images_df.image_id.str.endswith("_0") | images_df.image_id.str.endswith("_1"))]
    assert len(clean_night) > 0

    for _, r in clean_night.iterrows():
        p = sample_context.input_dir / r["path"]
        score, dtype, action, _ = _score_image(p, r["light"], r["camera_id"])
        # A normal clean night image must not be flagged as dark
        assert dtype != "dark", f"Clean night image {r.image_id} was falsely flagged as dark defect!"

    # Find a clean cam_B image
    clean_cam_b = images_df[(images_df.camera_id == "cam_B") & (images_df.image_id.str.endswith("_1"))]
    assert len(clean_cam_b) > 0

    for _, r in clean_cam_b.iterrows():
        p = sample_context.input_dir / r["path"]
        score, dtype, action, _ = _score_image(p, r["light"], r["camera_id"])
        # A normal clean cam_B image must not be flagged as blur
        assert dtype != "blur", f"Clean cam_B image {r.image_id} was falsely flagged as blur defect!"


def test_t02_decision_contract(sample_context: RunContext):
    """Test that decide() conforms to governance contract."""
    dummy_df = pd.DataFrame([
        {"image_id": "img_0", "score": 0.9, "pred_defect_type": "blur", "pred_action": "RECAPTURE"},
        {"image_id": "img_1", "score": 0.1, "pred_defect_type": "none", "pred_action": "KEEP"},
    ])

    dec = decide(sample_context, dummy_df)
    assert isinstance(dec, Decision)
    assert dec.status in ("GO", "HOLD", "REWORK")
    assert dec.reason_code != ""
    assert "Hoang Ba Dat" in dec.owner
    assert dec.scope == "t02"
