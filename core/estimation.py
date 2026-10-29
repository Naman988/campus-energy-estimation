"""Raw appliance and room-level energy estimation."""
from __future__ import annotations
import pandas as pd


def estimate_appliances(
    rooms: pd.DataFrame,
    appliances: pd.DataFrame,
    schedules: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate appliance kWh and retain whether a schedule was supplied.

    Formula: watts * quantity * hours_per_day * days_per_month / 1000.
    Appliances without a schedule are assigned zero hours and marked incomplete.
    """
    joined = appliances.merge(
        schedules,
        on=["room_id", "appliance"],
        how="left",
        indicator="_schedule_match",
        validate="one_to_one",
    )
    joined["has_schedule"] = joined["_schedule_match"].eq("both")
    joined = joined.drop(columns=["_schedule_match"])
    joined["hours_per_day"] = joined["hours_per_day"].fillna(0.0)
    joined["days_per_month"] = joined["days_per_month"].fillna(0.0)
    joined["raw_kwh"] = (
        joined["watts"] * joined["qty"] * joined["hours_per_day"] * joined["days_per_month"] / 1000.0
    )
    return joined.merge(
        rooms[["room_id", "block", "name", "room_type", "area_sqm"]],
        on="room_id",
        how="left",
        validate="many_to_one",
    )


def estimate_rooms(
    rooms: pd.DataFrame,
    appliances: pd.DataFrame,
    schedules: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return room estimates and per-appliance calculations."""
    details = estimate_appliances(rooms, appliances, schedules)
    totals = details.groupby("room_id", as_index=False).agg(
        raw_kwh=("raw_kwh", "sum"),
        appliances_count=("appliance", "count"),
        scheduled_count=("has_schedule", "sum"),
    )
    result = rooms.merge(totals, on="room_id", how="left", validate="one_to_one")
    result["raw_kwh"] = result["raw_kwh"].fillna(0.0)
    result["appliances_count"] = result["appliances_count"].fillna(0).astype(int)
    result["scheduled_count"] = result["scheduled_count"].fillna(0).astype(int)
    return result, details
