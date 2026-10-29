"""CSV loading and validation for campus energy data."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOM_COLUMNS = ["room_id", "block", "name", "room_type", "area_sqm"]
APPLIANCE_COLUMNS = ["room_id", "appliance", "watts", "qty"]
SCHEDULE_COLUMNS = ["room_id", "appliance", "hours_per_day", "days_per_month"]
METER_COLUMNS = ["block", "month", "measured_kwh"]
ROOM_TYPES = {"classroom", "lab", "office", "library", "hostel", "seminar"}


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required column(s): {', '.join(missing)}")


def validate_data(
    rooms: pd.DataFrame,
    appliances: pd.DataFrame,
    schedules: pd.DataFrame,
    meters: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Validate required columns, keys, references, and numeric ranges.

    Returns cleaned copies. Missing schedule rows are allowed and are interpreted as
    zero operating hours by the estimation module, as specified in the SRS.
    """
    frames = [rooms.copy(), appliances.copy(), schedules.copy(), meters.copy()]
    labels = ["rooms.csv", "appliances.csv", "schedules.csv", "meters.csv"]
    requirements = [ROOM_COLUMNS, APPLIANCE_COLUMNS, SCHEDULE_COLUMNS, METER_COLUMNS]
    for frame, required, label in zip(frames, requirements, labels):
        _require_columns(frame, required, label)

    rooms, appliances, schedules, meters = frames
    if rooms.empty:
        raise ValueError("rooms.csv has no rows. Add at least one room.")
    if appliances.empty:
        raise ValueError("appliances.csv has no rows. Add at least one appliance.")
    if meters.empty:
        raise ValueError("meters.csv has no rows. Add at least one meter reading.")

    # Keep identifiers as strings; spreadsheet exports can otherwise change their type.
    for frame, columns in [
        (rooms, ["room_id", "block", "name", "room_type"]),
        (appliances, ["room_id", "appliance"]),
        (schedules, ["room_id", "appliance"]),
        (meters, ["block", "month"]),
    ]:
        for column in columns:
            if frame[column].isna().any():
                raise ValueError(f"{column} contains blank values in one of the uploaded CSV files.")
            frame[column] = frame[column].astype(str).str.strip()
            if (frame[column] == "").any():
                raise ValueError(f"{column} contains blank values in one of the uploaded CSV files.")

    if rooms["room_id"].duplicated().any():
        duplicate = rooms.loc[rooms["room_id"].duplicated(), "room_id"].iloc[0]
        raise ValueError(f"rooms.csv contains duplicate room_id '{duplicate}'.")
    if appliances.duplicated(["room_id", "appliance"]).any():
        raise ValueError("appliances.csv has duplicate (room_id, appliance) pairs.")
    if schedules.duplicated(["room_id", "appliance"]).any():
        raise ValueError("schedules.csv has duplicate (room_id, appliance) pairs.")
    if meters.duplicated(["block", "month"]).any():
        raise ValueError("meters.csv has duplicate (block, month) rows.")

    for frame, columns, label in [
        (rooms, ["area_sqm"], "rooms.csv"),
        (appliances, ["watts", "qty"], "appliances.csv"),
        (schedules, ["hours_per_day", "days_per_month"], "schedules.csv"),
        (meters, ["measured_kwh"], "meters.csv"),
    ]:
        for column in columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
            if frame[column].isna().any():
                raise ValueError(f"{label}: '{column}' must contain valid numeric values.")

    if (rooms["area_sqm"] <= 0).any():
        raise ValueError("rooms.csv: area_sqm must be greater than zero.")
    if (appliances["watts"] < 0).any():
        raise ValueError("appliances.csv: watts cannot be negative.")
    if (appliances["qty"] < 1).any() or ((appliances["qty"] % 1) != 0).any():
        raise ValueError("appliances.csv: qty must be a positive whole number.")
    if ((schedules["hours_per_day"] < 0) | (schedules["hours_per_day"] > 24)).any():
        raise ValueError("schedules.csv: hours_per_day must be between 0 and 24.")
    if ((schedules["days_per_month"] < 0) | (schedules["days_per_month"] > 31)).any():
        raise ValueError("schedules.csv: days_per_month must be between 0 and 31.")
    if (meters["measured_kwh"] < 0).any():
        raise ValueError("meters.csv: measured_kwh cannot be negative.")

    invalid_types = sorted(set(rooms["room_type"].str.lower()) - ROOM_TYPES)
    if invalid_types:
        raise ValueError("rooms.csv: unsupported room_type value(s): " + ", ".join(invalid_types))
    rooms["room_type"] = rooms["room_type"].str.lower()

    room_ids = set(rooms["room_id"])
    for label, frame in [("appliances.csv", appliances), ("schedules.csv", schedules)]:
        unknown = sorted(set(frame["room_id"]) - room_ids)
        if unknown:
            raise ValueError(f"{label} references room_id(s) not found in rooms.csv: {', '.join(unknown[:5])}")

    known_blocks = set(rooms["block"])
    unknown_blocks = sorted(set(meters["block"]) - known_blocks)
    if unknown_blocks:
        raise ValueError("meters.csv references block(s) not present in rooms.csv: " + ", ".join(unknown_blocks))

    invalid_months = ~meters["month"].str.match(r"^\d{4}-(0[1-9]|1[0-2])$")
    if invalid_months.any():
        raise ValueError("meters.csv: month must use YYYY-MM format, such as 2026-09.")

    return rooms, appliances, schedules, meters


def load_csv_directory(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and validate the four SRS CSV files from a directory."""
    data_path = Path(data_dir)
    filenames = ["rooms.csv", "appliances.csv", "schedules.csv", "meters.csv"]
    missing = [name for name in filenames if not (data_path / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing data file(s) in {data_path}: {', '.join(missing)}")
    frames = [pd.read_csv(data_path / name) for name in filenames]
    return validate_data(*frames)
