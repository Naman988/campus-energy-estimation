"""Confidence scoring for estimated room-level energy values."""
from __future__ import annotations
import numpy as np
import pandas as pd


def add_confidence_scores(room_results: pd.DataFrame) -> pd.DataFrame:
    """Attach the SRS confidence score (0-100) and High/Medium/Low label."""
    result = room_results.copy()
    raw = result["raw_kwh"].to_numpy(dtype=float)
    calibrated = result["calibrated_kwh"].fillna(0).to_numpy(dtype=float)
    factor = np.divide(calibrated, raw, out=np.ones_like(calibrated), where=raw > 1e-12)
    closeness = np.maximum(0.0, 1.0 - np.abs(factor - 1.0) / 0.5)
    count = result["appliances_count"].to_numpy(dtype=float)
    scheduled = result["scheduled_count"].to_numpy(dtype=float)
    completeness = np.divide(scheduled, count, out=np.zeros_like(count), where=count > 0)
    score = 100.0 * (0.6 * closeness + 0.4 * completeness)
    result["calibration_factor"] = factor
    result["confidence_score"] = np.clip(score, 0.0, 100.0).round(1)
    result["confidence_label"] = np.select(
        [result["confidence_score"] >= 75, result["confidence_score"] >= 50],
        ["High", "Medium"],
        default="Low",
    )
    result["completeness"] = completeness.round(3)
    return result
