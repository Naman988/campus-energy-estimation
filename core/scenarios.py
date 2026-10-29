"""What-if energy-saving scenarios based on the baseline calibration factors."""
from __future__ import annotations
import pandas as pd
from .estimation import estimate_appliances


def run_scenario(
    rooms: pd.DataFrame,
    appliances: pd.DataFrame,
    schedules: pd.DataFrame,
    baseline_rooms: pd.DataFrame,
    emission_factor: float = 0.82,
    ac_hours_reduction: float = 0.0,
    lighting_watt_reduction_pct: float = 0.0,
    computer_hours_reduction_pct: float = 0.0,
    days_reduction: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the four SRS levers and return room results plus changed appliances.

    The scenario uses each room's baseline calibration factor, as specified by the
    SRS. It is a modelled what-if estimate, not a newly measured meter reading.
    """
    if ac_hours_reduction < 0 or days_reduction < 0:
        raise ValueError("Reductions cannot be negative.")
    if not 0 <= lighting_watt_reduction_pct <= 100:
        raise ValueError("Lighting watt reduction must be between 0 and 100%.")
    if not 0 <= computer_hours_reduction_pct <= 100:
        raise ValueError("Computer hours reduction must be between 0 and 100%.")

    details = estimate_appliances(rooms, appliances, schedules)
    modified = details.copy()
    labels = modified["appliance"].astype(str).str.lower().str.strip()
    is_ac = labels.isin({"ac", "air conditioner", "air-conditioning", "air conditioning"})
    is_lights = labels.isin({"light", "lights", "lighting", "led", "led lights"})
    is_computer = labels.isin({"computer", "computers", "desktop", "pc"})

    modified.loc[is_ac, "hours_per_day"] = (modified.loc[is_ac, "hours_per_day"] - float(ac_hours_reduction)).clip(lower=0.0)
    modified.loc[is_lights, "watts"] = modified.loc[is_lights, "watts"] * (1.0 - lighting_watt_reduction_pct / 100.0)
    modified.loc[is_computer, "hours_per_day"] = modified.loc[is_computer, "hours_per_day"] * (1.0 - computer_hours_reduction_pct / 100.0)
    modified["days_per_month"] = (modified["days_per_month"] - int(days_reduction)).clip(lower=0.0)
    modified["scenario_raw_kwh"] = (
        modified["watts"] * modified["qty"] * modified["hours_per_day"] * modified["days_per_month"] / 1000.0
    )

    scenario_raw = modified.groupby("room_id", as_index=False)["scenario_raw_kwh"].sum()
    factors = baseline_rooms[["room_id", "calibrated_kwh", "calibration_factor"]].copy()
    factors = factors.rename(columns={"calibrated_kwh": "baseline_kwh"})
    result = rooms.merge(scenario_raw, on="room_id", how="left", validate="one_to_one")
    result = result.merge(factors, on="room_id", how="left", validate="one_to_one")
    result["scenario_raw_kwh"] = result["scenario_raw_kwh"].fillna(0.0)
    result["calibration_factor"] = result["calibration_factor"].fillna(1.0)
    result["scenario_kwh"] = result["scenario_raw_kwh"] * result["calibration_factor"]
    result["saved_kwh"] = (result["baseline_kwh"] - result["scenario_kwh"]).clip(lower=0.0)
    result["baseline_carbon_kg"] = result["baseline_kwh"] * float(emission_factor)
    result["scenario_carbon_kg"] = result["scenario_kwh"] * float(emission_factor)
    result["saved_carbon_kg"] = result["saved_kwh"] * float(emission_factor)
    return result, modified
