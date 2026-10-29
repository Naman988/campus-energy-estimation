"""Calibration that reconciles raw room estimates with block meter readings."""
from __future__ import annotations
from collections.abc import Sequence
import numpy as np
import pandas as pd


def calibrate_values(raw_values: Sequence[float], measured_kwh: float, method: str = "proportional") -> np.ndarray:
    """Calibrate non-negative raw estimates to a measured block total.

    Proportional: x_i = r_i * (M / R).
    Weighted: x_i = r_i + mu*r_i^2 where mu=(M-R)/sum(r_i^2).
    Weighted results that become negative fall back to proportional scaling.

    Edge-case clarification: if the raw total is zero and the meter reading is
    positive, no distribution can satisfy both the zero-room rule and the meter
    total invariant, so a clear ValueError is raised instead of inventing data.
    """
    raw = np.asarray(list(raw_values), dtype=float)
    measured = float(measured_kwh)
    if raw.ndim != 1:
        raise ValueError("Raw estimates must be a one-dimensional sequence.")
    if not np.all(np.isfinite(raw)) or not np.isfinite(measured):
        raise ValueError("Energy estimates and meter readings must be finite numbers.")
    if np.any(raw < 0) or measured < 0:
        raise ValueError("Energy estimates and meter readings cannot be negative.")
    if method not in {"proportional", "weighted"}:
        raise ValueError("Calibration method must be 'proportional' or 'weighted'.")

    total_raw = float(raw.sum())
    if total_raw <= 1e-12:
        if measured <= 1e-12:
            return np.zeros_like(raw)
        raise ValueError("Cannot calibrate a positive meter total because all raw room estimates are zero.")
    if measured <= 1e-12:
        return np.zeros_like(raw)

    proportional = raw * (measured / total_raw)
    if method == "proportional":
        calibrated = proportional
    else:
        denominator = float(np.square(raw).sum())
        mu = (measured - total_raw) / denominator
        weighted = raw + mu * np.square(raw)
        calibrated = proportional if np.any(weighted < -1e-9) else np.maximum(weighted, 0.0)

    # Absorb tiny floating-point drift so the total matches the meter exactly.
    correction = measured - float(calibrated.sum())
    positive_positions = np.flatnonzero(calibrated > 0)
    if positive_positions.size:
        calibrated[positive_positions[-1]] += correction
    elif measured > 1e-12:
        raise ValueError("Calibration could not allocate a positive meter total.")
    return calibrated


def calibrate_rooms(room_estimates: pd.DataFrame, meters: pd.DataFrame, method: str = "proportional") -> pd.DataFrame:
    """Add measured totals, calibrated kWh, and calibration factors to room rows."""
    result = room_estimates.copy()
    result = result.merge(meters[["block", "month", "measured_kwh"]], on="block", how="left", validate="many_to_many")
    if "month" not in result.columns:
        raise ValueError("No month value was provided in the meter table.")

    calibrated_chunks = []
    for (block, month), group in result.groupby(["block", "month"], sort=False, dropna=False):
        measured_values = group["measured_kwh"].dropna().unique()
        if len(measured_values) == 0:
            group = group.copy()
            group["calibrated_kwh"] = np.nan
            calibrated_chunks.append(group)
            continue
        if len(measured_values) > 1:
            raise ValueError(f"Block {block} has multiple meter readings for {month}.")
        measured = float(measured_values[0])
        group = group.copy()
        group["calibrated_kwh"] = calibrate_values(group["raw_kwh"].to_numpy(), measured, method)
        raw = group["raw_kwh"].to_numpy(dtype=float)
        cal = group["calibrated_kwh"].to_numpy(dtype=float)
        group["calibration_factor"] = np.divide(cal, raw, out=np.ones_like(cal), where=raw > 1e-12)
        calibrated_chunks.append(group)
    return pd.concat(calibrated_chunks, ignore_index=True) if calibrated_chunks else result
