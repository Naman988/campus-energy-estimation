"""Unit tests for the core energy calculations."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.calibration import calibrate_values
from core.carbon import add_carbon_estimates
from core.confidence import add_confidence_scores
from core.estimation import estimate_rooms
from core.scenarios import run_scenario
from core.data_loader import load_csv_directory


def test_raw_appliance_formula_and_missing_schedule():
    rooms = pd.DataFrame([{"room_id": "R1", "block": "A", "name": "Room", "room_type": "classroom", "area_sqm": 20.0}])
    appliances = pd.DataFrame([
        {"room_id": "R1", "appliance": "Lights", "watts": 100.0, "qty": 2},
        {"room_id": "R1", "appliance": "Fan", "watts": 50.0, "qty": 1},
    ])
    schedules = pd.DataFrame([{"room_id": "R1", "appliance": "Lights", "hours_per_day": 5.0, "days_per_month": 20}])
    estimates, details = estimate_rooms(rooms, appliances, schedules)
    assert details.loc[details.appliance == "Lights", "raw_kwh"].iloc[0] == pytest.approx(20.0)
    assert details.loc[details.appliance == "Fan", "raw_kwh"].iloc[0] == pytest.approx(0.0)
    assert estimates["scheduled_count"].iloc[0] == 1
    assert estimates["appliances_count"].iloc[0] == 2


@pytest.mark.parametrize("method", ["proportional", "weighted"])
def test_calibration_sum_invariant(method):
    raw = [100.0, 250.0, 75.0, 0.0]
    measured = 510.0
    calibrated = calibrate_values(raw, measured, method)
    assert np.all(calibrated >= 0)
    assert calibrated.sum() == pytest.approx(measured, abs=1e-6)
    assert calibrated[3] == 0.0


def test_weighted_calibration_falls_back_when_negative():
    calibrated = calibrate_values([1.0, 100.0], 10.0, "weighted")
    assert calibrated.sum() == pytest.approx(10.0, abs=1e-6)
    assert np.all(calibrated >= 0)


def test_zero_raw_and_zero_meter_returns_zeros():
    assert np.array_equal(calibrate_values([0.0, 0.0], 0.0), np.array([0.0, 0.0]))


def test_zero_raw_with_positive_meter_is_reported():
    with pytest.raises(ValueError):
        calibrate_values([0.0, 0.0], 10.0)


def test_confidence_bounds_and_labels():
    frame = pd.DataFrame({
        "raw_kwh": [100.0, 100.0, 0.0],
        "calibrated_kwh": [100.0, 160.0, 0.0],
        "appliances_count": [2, 2, 0],
        "scheduled_count": [2, 1, 0],
    })
    result = add_confidence_scores(frame)
    assert result["confidence_score"].between(0, 100).all()
    assert result.loc[0, "confidence_label"] == "High"
    assert result.loc[1, "confidence_label"] in {"Low", "Medium"}


def test_scenario_savings_are_non_negative():
    data_dir = ROOT / "data"
    rooms, appliances, schedules, meters = load_csv_directory(data_dir)
    from core.calibration import calibrate_rooms
    estimates, _ = estimate_rooms(rooms, appliances, schedules)
    all_months = calibrate_rooms(estimates, meters, "proportional")
    baseline = all_months[all_months["month"] == "2026-09"].copy()
    scenario, _ = run_scenario(
        rooms, appliances, schedules, baseline,
        ac_hours_reduction=2.0,
        lighting_watt_reduction_pct=20.0,
        computer_hours_reduction_pct=25.0,
        days_reduction=1,
    )
    assert (scenario["saved_kwh"] >= -1e-9).all()
    assert scenario["saved_kwh"].sum() >= 0


def test_emissions_formula():
    frame = pd.DataFrame({"calibrated_kwh": [10.0, 20.0]})
    result = add_carbon_estimates(frame, 0.82)
    assert result["carbon_kg"].tolist() == pytest.approx([8.2, 16.4])


def test_generated_data_is_loadable():
    rooms, appliances, schedules, meters = load_csv_directory(ROOT / "data")
    assert len(rooms) == 16
    assert set(meters["month"]) == {"2026-07", "2026-08", "2026-09"}
    assert len(meters) == 9
