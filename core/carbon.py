"""Carbon footprint calculations."""
from __future__ import annotations
import pandas as pd


def add_carbon_estimates(frame: pd.DataFrame, emission_factor: float = 0.82) -> pd.DataFrame:
    """Add kg CO2 estimates using calibrated kWh times kg CO2 per kWh."""
    if emission_factor < 0:
        raise ValueError("Emission factor cannot be negative.")
    result = frame.copy()
    result["carbon_kg"] = result["calibrated_kwh"].fillna(0.0) * float(emission_factor)
    return result
