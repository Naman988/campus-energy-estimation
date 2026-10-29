"""Transparent, rule-based waste flags for the Major Project preview."""
from __future__ import annotations
import pandas as pd

DEFAULT_MAX_HOURS = {"AC": 10.0, "Lights": 12.0, "Computer": 10.0, "Projector": 8.0, "Fan": 12.0}


def detect_waste(
    room_results: pd.DataFrame,
    appliance_details: pd.DataFrame,
    threshold_multiplier: float = 1.5,
    max_hours: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return room-intensity flags and appliance-hours flags."""
    if threshold_multiplier <= 0:
        raise ValueError("Threshold multiplier must be greater than zero.")
    limits = DEFAULT_MAX_HOURS.copy()
    if max_hours:
        limits.update(max_hours)

    rooms = room_results.copy()
    rooms["intensity_kwh_per_sqm"] = rooms["calibrated_kwh"].fillna(0.0) / rooms["area_sqm"].clip(lower=1e-12)
    medians = rooms.groupby("room_type")["intensity_kwh_per_sqm"].median().rename("type_median_intensity")
    rooms = rooms.join(medians, on="room_type")
    rooms["intensity_threshold"] = rooms["type_median_intensity"] * float(threshold_multiplier)
    rooms["room_waste_flag"] = rooms["intensity_kwh_per_sqm"] > rooms["intensity_threshold"]
    rooms["room_flag_reason"] = rooms["room_waste_flag"].map(
        {True: "Intensity exceeds the room-type median threshold", False: "No intensity flag"}
    )

    appliances = appliance_details.copy()
    appliances["hours_limit"] = appliances["appliance"].map(limits)
    appliances["hours_waste_flag"] = (
        appliances["hours_limit"].notna()
        & (appliances["hours_per_day"] > appliances["hours_limit"])
    )
    appliances["appliance_flag_reason"] = appliances["hours_waste_flag"].map(
        {True: "Operating hours exceed configured limit", False: "No hours flag"}
    )
    flagged_appliances = appliances[appliances["hours_waste_flag"]].copy()
    return rooms, flagged_appliances
