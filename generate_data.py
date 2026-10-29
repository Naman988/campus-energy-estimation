"""Generate deterministic sample CSV data for the campus energy demo."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MONTHS = ["2026-07", "2026-08", "2026-09"]


def generate_sample_data(output_dir: str | Path = DATA_DIR) -> None:
    """Create 16 illustrative rooms, appliance/schedule data, and meter readings."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    room_specs = [
        ("A101", "A", "Lecture Room 101", "classroom", 62),
        ("A102", "A", "Computer Lab 102", "lab", 88),
        ("A103", "A", "Faculty Office 103", "office", 38),
        ("A104", "A", "Lecture Room 104", "classroom", 58),
        ("A105", "A", "Central Reading Room", "library", 125),
        ("A106", "A", "Seminar Hall 106", "seminar", 94),
        ("B201", "B", "Lecture Room 201", "classroom", 66),
        ("B202", "B", "Electronics Lab 202", "lab", 96),
        ("B203", "B", "Admin Office 203", "office", 42),
        ("B204", "B", "Lecture Room 204", "classroom", 56),
        ("B205", "B", "Library Annex", "library", 112),
        ("C301", "C", "Student Hostel Common Room", "hostel", 91),
        ("C302", "C", "Lecture Room 302", "classroom", 73),
        ("C303", "C", "Mechanical Lab 303", "lab", 108),
        ("C304", "C", "Department Office 304", "office", 40),
        ("C305", "C", "Seminar Hall 305", "seminar", 86),
    ]
    rooms = pd.DataFrame(room_specs, columns=["room_id", "block", "name", "room_type", "area_sqm"])

    appliance_rows: list[dict] = []
    schedule_rows: list[dict] = []
    for room in room_specs:
        room_id, block, name, room_type, area = room
        # All rooms get lighting and fans; room type determines additional equipment.
        equipment = [
            ("Lights", 40, max(6, int(area / 6.5))),
            ("Fan", 70, max(2, int(area / 13))),
            ("AC", 1500, 1 if area < 65 else (2 if area < 100 else 3)),
        ]
        if room_type == "lab":
            equipment += [("Computer", 160, 16 if area > 90 else 12), ("Projector", 250, 1)]
        elif room_type == "office":
            equipment += [("Computer", 160, 4), ("Printer", 350, 1)]
        elif room_type == "library":
            equipment += [("Computer", 160, 8), ("Projector", 250, 1)]
        elif room_type == "seminar":
            equipment += [("Projector", 250, 2), ("Computer", 160, 1)]
        elif room_type == "hostel":
            equipment += [("Refrigerator", 180, 2)]

        for appliance, watts, qty in equipment:
            appliance_rows.append({"room_id": room_id, "appliance": appliance, "watts": watts, "qty": qty})
            if appliance == "Lights":
                hours, days = 10.0, 26 if room_type in {"library", "hostel"} else 22
            elif appliance == "Fan":
                hours, days = 9.0, 26 if room_type in {"library", "hostel"} else 22
            elif appliance == "AC":
                hours, days = 14.0 if room_id in {"A102", "C303"} else 7.5, 26 if room_type in {"library", "hostel"} else 22
            elif appliance == "Computer":
                hours = 12.0 if room_id in {"A102", "C303"} else (8.5 if room_type == "lab" else 6.0)
                days = 26 if room_type in {"library", "hostel"} else 22
            elif appliance == "Projector":
                hours, days = 9.0 if room_id == "A106" else 5.0, 22
            elif appliance == "Printer":
                hours, days = 2.0, 22
            else:  # refrigerator
                hours, days = 12.0, 30
            # Deterministic, small variation by equipment/room prevents overly uniform rows.
            hours = max(0.0, hours + float(rng.choice([0.0, 0.0, 0.5, -0.5])))
            schedule_rows.append({
                "room_id": room_id,
                "appliance": appliance,
                "hours_per_day": round(hours, 1),
                "days_per_month": int(days),
            })

    appliances = pd.DataFrame(appliance_rows)
    schedules = pd.DataFrame(schedule_rows)
    # Deliberately omit one schedule to demonstrate the completeness score and missing-row handling.
    schedules = schedules[~((schedules["room_id"] == "B203") & (schedules["appliance"] == "Printer"))].reset_index(drop=True)

    energy = appliances.merge(schedules, on=["room_id", "appliance"], how="left")
    energy["hours_per_day"] = energy["hours_per_day"].fillna(0.0)
    energy["days_per_month"] = energy["days_per_month"].fillna(0.0)
    energy["raw_kwh"] = energy["watts"] * energy["qty"] * energy["hours_per_day"] * energy["days_per_month"] / 1000.0
    room_raw = energy.merge(rooms[["room_id", "block"]], on="room_id").groupby("block")["raw_kwh"].sum()

    meter_rows = []
    for month in MONTHS:
        for block in ["A", "B", "C"]:
            multiplier = float(rng.uniform(0.85, 1.25))
            measured = float(room_raw.loc[block]) * multiplier
            meter_rows.append({"block": block, "month": month, "measured_kwh": round(measured, 3)})
    meters = pd.DataFrame(meter_rows)

    rooms.to_csv(output_path / "rooms.csv", index=False)
    appliances.to_csv(output_path / "appliances.csv", index=False)
    schedules.to_csv(output_path / "schedules.csv", index=False)
    meters.to_csv(output_path / "meters.csv", index=False)


if __name__ == "__main__":
    generate_sample_data()
    print(f"Generated sample data in {DATA_DIR}")
