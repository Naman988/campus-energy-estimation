"""Streamlit frontend for Campus Energy Estimation and Sustainability Analytics."""
from __future__ import annotations
import io
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from core.calibration import calibrate_rooms
from core.carbon import add_carbon_estimates
from core.confidence import add_confidence_scores
from core.data_loader import load_csv_directory, validate_data
from core.estimation import estimate_appliances, estimate_rooms
from core.report import build_markdown_report
from core.scenarios import run_scenario
from core.waste import DEFAULT_MAX_HOURS, detect_waste
from generate_data import generate_sample_data

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

st.set_page_config(
    page_title="Campus Energy Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _read_upload(upload) -> pd.DataFrame:
    """Read a Streamlit-uploaded CSV without writing it to disk."""
    return pd.read_csv(io.BytesIO(upload.getvalue()))


def _format_number(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}"


def _prepare_data():
    """Read sample CSVs by default, replacing them only when all four uploads exist."""
    expected = ["rooms.csv", "appliances.csv", "schedules.csv", "meters.csv"]
    if not all((DATA_DIR / name).exists() for name in expected):
        generate_sample_data(DATA_DIR)

    uploads = {}
    st.sidebar.markdown("### Data source")
    st.sidebar.caption("Upload all four CSV files to replace the included sample dataset.")
    for name in expected:
        uploads[name] = st.sidebar.file_uploader(name, type=["csv"], key=f"upload_{name}")

    supplied_count = sum(value is not None for value in uploads.values())
    sample_data = True
    error_message = None
    if supplied_count == len(expected):
        try:
            frames = [
                _read_upload(uploads["rooms.csv"]),
                _read_upload(uploads["appliances.csv"]),
                _read_upload(uploads["schedules.csv"]),
                _read_upload(uploads["meters.csv"]),
            ]
            data = validate_data(*frames)
            sample_data = False
        except Exception as exc:
            data = load_csv_directory(DATA_DIR)
            error_message = str(exc)
    else:
        data = load_csv_directory(DATA_DIR)
        if supplied_count > 0:
            st.sidebar.warning("Sample data is active. Upload all four CSVs together to switch datasets.")

    if error_message:
        st.sidebar.error(f"Upload validation failed: {error_message}")
        st.sidebar.info("The app has kept the built-in sample data active.")
    return data, sample_data


def _make_block_summary(frame: pd.DataFrame) -> pd.DataFrame:
    meter = frame.groupby("block", as_index=False).agg(measured_kwh=("measured_kwh", "first"))
    allocated = frame.groupby("block", as_index=False).agg(calibrated_kwh=("calibrated_kwh", "sum"))
    result = meter.merge(allocated, on="block", how="outer")
    result["difference_kwh"] = result["calibrated_kwh"] - result["measured_kwh"]
    result["verified"] = result["difference_kwh"].abs() <= 1e-6
    return result.sort_values("block")


# Load data and calculate the chosen calibration method.
(rooms, appliances, schedules, meters), sample_data = _prepare_data()
method = st.sidebar.selectbox("Calibration method", ["proportional", "weighted"], index=0)
emission_factor = st.sidebar.number_input(
    "Emission factor (kg CO₂/kWh)", min_value=0.0, max_value=3.0, value=0.82, step=0.01,
    help="Editable assumption from the SRS. Use a documented factor appropriate to the reporting period for formal reporting.",
)

try:
    room_estimates, appliance_details = estimate_rooms(rooms, appliances, schedules)
    all_calibrated = calibrate_rooms(room_estimates, meters, method=method)
    all_results = add_confidence_scores(all_calibrated)
except Exception as exc:
    st.error(f"The data could not be processed: {exc}")
    st.stop()

months = sorted(meters["month"].unique().tolist())
selected_month = st.sidebar.selectbox("Meter month", months, index=len(months) - 1)
selected = all_results[all_results["month"] == selected_month].copy()
selected = add_carbon_estimates(selected, emission_factor)
block_summary = _make_block_summary(selected)
all_verified = bool(block_summary["verified"].all()) and not selected["measured_kwh"].isna().any()

st.title("⚡ Campus Energy Estimation & Sustainability Analytics")
st.caption("Estimate room-level electricity use from appliance inventories, schedules and aggregate block meter readings.")
if sample_data:
    st.info("**SAMPLE DATA** — These values are synthetic and intended for demonstration, not real campus readings.")
else:
    st.success("Using validated user-uploaded CSV data.")
st.caption("Room-level values are estimates; no room-level meter ground truth is available. Carbon figures depend on the selected emission factor.")

page = st.sidebar.radio(
    "Navigate",
    ["Campus Dashboard", "Room Analysis", "Scenario Simulator", "Waste Preview", "Data & Exports"],
)

if page == "Campus Dashboard":
    st.subheader(f"Campus overview · {selected_month}")
    total_meter = float(block_summary["measured_kwh"].sum())
    total_calibrated = float(selected["calibrated_kwh"].sum())
    total_carbon = float(selected["carbon_kg"].sum())
    total_rooms = int(selected["room_id"].nunique())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Measured block electricity", f"{_format_number(total_meter)} kWh")
    c2.metric("Allocated room electricity", f"{_format_number(total_calibrated)} kWh")
    c3.metric("Estimated carbon footprint", f"{_format_number(total_carbon)} kg CO₂")
    c4.metric("Rooms included", str(total_rooms))

    if all_verified:
        st.success("✓ Calibration verified: room allocations sum to the measured total for every block.")
    else:
        st.warning("At least one block could not be reconciled. Check that its raw estimates and meter reading are both available.")

    col1, col2 = st.columns([1.25, 1])
    with col1:
        st.markdown("#### Meter reading vs. room allocation")
        chart = block_summary.melt(
            id_vars="block", value_vars=["measured_kwh", "calibrated_kwh"],
            var_name="series", value_name="energy_kwh",
        )
        chart["series"] = chart["series"].map({"measured_kwh": "Measured block total", "calibrated_kwh": "Calibrated room total"})
        fig = px.bar(chart, x="block", y="energy_kwh", color="series", barmode="group", labels={"block": "Block", "energy_kwh": "Energy (kWh)", "series": "Series"})
        fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("#### Confidence distribution")
        confidence_counts = selected["confidence_label"].value_counts().reindex(["High", "Medium", "Low"], fill_value=0).rename_axis("confidence").reset_index(name="rooms")
        fig = px.pie(confidence_counts, names="confidence", values="rooms", hole=0.55)
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Block reconciliation")
    display_blocks = block_summary.copy()
    for col in ["measured_kwh", "calibrated_kwh", "difference_kwh"]:
        display_blocks[col] = display_blocks[col].round(6 if col == "difference_kwh" else 2)
    st.dataframe(display_blocks, use_container_width=True, hide_index=True)

    st.markdown("#### Highest calibrated room consumption")
    top = selected.sort_values("calibrated_kwh", ascending=False).head(6)
    fig = px.bar(top, x="room_id", y="calibrated_kwh", color="block", hover_data=["name", "room_type"], labels={"room_id": "Room", "calibrated_kwh": "Calibrated kWh"})
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

elif page == "Room Analysis":
    st.subheader(f"Room-level energy analysis · {selected_month}")
    block_options = ["All blocks"] + sorted(selected["block"].unique().tolist())
    chosen_block = st.selectbox("Filter by block", block_options)
    visible = selected.copy() if chosen_block == "All blocks" else selected[selected["block"] == chosen_block].copy()

    compare = visible.melt(
        id_vars=["room_id", "name", "block"], value_vars=["raw_kwh", "calibrated_kwh"],
        var_name="series", value_name="energy_kwh",
    )
    compare["series"] = compare["series"].map({"raw_kwh": "Raw estimate", "calibrated_kwh": "Calibrated estimate"})
    fig = px.bar(compare, x="room_id", y="energy_kwh", color="series", barmode="group", hover_data=["name", "block"], labels={"room_id": "Room", "energy_kwh": "Energy (kWh)", "series": "Estimate"})
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    show_cols = ["room_id", "name", "block", "room_type", "area_sqm", "raw_kwh", "measured_kwh", "calibrated_kwh", "calibration_factor", "confidence_score", "confidence_label", "carbon_kg"]

    room_table = visible[show_cols].round(3).rename(
    columns={"measured_kwh": "block_meter_kwh"}
    )

    st.dataframe(room_table, use_container_width=True, hide_index=True)
    st.caption("Confidence = 60% calibration closeness + 40% appliance-schedule completeness. It is a heuristic score, not a statistical probability.")

elif page == "Scenario Simulator":
    st.subheader("What-if energy-saving simulator")
    st.write("Adjust one or more levers. Results update immediately using the room's baseline calibration factor.")
    st.info("Scenario figures are modelled estimates compared with the selected month's baseline, not newly measured electricity savings.")
    left, right = st.columns(2)
    with left:
        ac_reduction = st.slider("Reduce AC operating time (hours/day)", 0.0, 8.0, 2.0, 0.5)
        led_reduction = st.slider("Lighting watt reduction (LED improvement, %)", 0, 80, 20, 5)
    with right:
        computer_reduction = st.slider("Reduce computer operating hours (%)", 0, 100, 25, 5)
        days_reduction = st.slider("Reduce operating days per month for all appliances", 0, 10, 0, 1)

    scenario, changed_appliances = run_scenario(
        rooms, appliances, schedules, selected,
        emission_factor=emission_factor,
        ac_hours_reduction=ac_reduction,
        lighting_watt_reduction_pct=float(led_reduction),
        computer_hours_reduction_pct=float(computer_reduction),
        days_reduction=days_reduction,
    )
    baseline_kwh = float(scenario["baseline_kwh"].sum())
    scenario_kwh = float(scenario["scenario_kwh"].sum())
    saved_kwh = float(scenario["saved_kwh"].sum())
    saved_carbon = float(scenario["saved_carbon_kg"].sum())
    a, b, c, d = st.columns(4)
    a.metric("Baseline room allocation", f"{_format_number(baseline_kwh)} kWh")
    b.metric("Scenario estimate", f"{_format_number(scenario_kwh)} kWh", delta=f"{_format_number(scenario_kwh - baseline_kwh)} kWh")
    c.metric("Modelled energy saved", f"{_format_number(saved_kwh)} kWh")
    d.metric("Modelled CO₂ saved", f"{_format_number(saved_carbon)} kg")

    block_scenario = scenario.groupby("block", as_index=False).agg(baseline_kwh=("baseline_kwh", "sum"), scenario_kwh=("scenario_kwh", "sum"), saved_kwh=("saved_kwh", "sum"))
    chart = block_scenario.melt(id_vars="block", value_vars=["baseline_kwh", "scenario_kwh"], var_name="series", value_name="energy_kwh")
    chart["series"] = chart["series"].map({"baseline_kwh": "Baseline", "scenario_kwh": "Scenario"})
    fig = px.bar(chart, x="block", y="energy_kwh", color="series", barmode="group", labels={"block": "Block", "energy_kwh": "Energy (kWh)", "series": "Estimate"})
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Savings by room")
    st.dataframe(scenario[["room_id", "block", "name", "baseline_kwh", "scenario_kwh", "saved_kwh", "saved_carbon_kg"]].round(3), use_container_width=True, hide_index=True)

elif page == "Waste Preview":
    st.subheader("Rule-based waste detection")
    st.warning("**Preview of Major Project scope** — These are transparent rule-based flags, not ML predictions or verified proof of waste.")
    threshold = st.slider("Room intensity threshold multiplier", min_value=0.5, max_value=3.0, value=1.5, step=0.1)
    st.markdown("#### Maximum expected appliance hours per day")
    controls = st.columns(5)
    editable_limits = {}
    for column, (name, default) in zip(controls, DEFAULT_MAX_HOURS.items()):
        with column:
            editable_limits[name] = st.number_input(name, min_value=0.0, max_value=24.0, value=float(default), step=1.0)

    room_flags, appliance_flags = detect_waste(selected, appliance_details, threshold_multiplier=threshold, max_hours=editable_limits)
    flagged_rooms = room_flags[room_flags["room_waste_flag"]]
    st.metric("Rooms flagged for high intensity", len(flagged_rooms))
    st.markdown("#### Room energy intensity")
    room_cols = ["room_id", "name", "block", "room_type", "area_sqm", "calibrated_kwh", "intensity_kwh_per_sqm", "type_median_intensity", "intensity_threshold", "room_waste_flag", "room_flag_reason"]
    st.dataframe(room_flags[room_cols].round(3), use_container_width=True, hide_index=True)
    st.markdown("#### Appliances exceeding their hours threshold")
    if appliance_flags.empty:
        st.success("No appliance-hours flags for the current thresholds.")
    else:
        st.dataframe(appliance_flags[["room_id", "block", "appliance", "hours_per_day", "hours_limit", "appliance_flag_reason"]].round(2), use_container_width=True, hide_index=True)
    st.caption("Room intensity = calibrated kWh ÷ room area. A room is flagged when its intensity exceeds the selected multiplier of the median for its room type.")

elif page == "Data & Exports":
    st.subheader("Data and report exports")
    st.write("The prototype stores its example data in four CSV files and does not require a database server.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Validated input data")
        st.write(f"Rooms: **{len(rooms)}** · Appliance records: **{len(appliances)}** · Schedules: **{len(schedules)}** · Meter readings: **{len(meters)}**")
        with st.expander("Preview rooms.csv"):
            st.dataframe(rooms, use_container_width=True, hide_index=True)
        with st.expander("Preview appliances.csv"):
            st.dataframe(appliances, use_container_width=True, hide_index=True)
        with st.expander("Preview schedules.csv"):
            st.dataframe(schedules, use_container_width=True, hide_index=True)
        with st.expander("Preview meters.csv"):
            st.dataframe(meters, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("#### Download results")
        export_cols = ["room_id", "block", "name", "room_type", "area_sqm", "raw_kwh", "measured_kwh", "calibrated_kwh", "calibration_factor", "confidence_score", "confidence_label", "carbon_kg"]
        export_df = selected[export_cols].sort_values(["block", "room_id"]).round(4)
        st.download_button(
            "Download calibrated room CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"calibrated_rooms_{selected_month}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        markdown_report = build_markdown_report(selected, selected_month, method, emission_factor, sample_data)
        st.download_button(
            "Download Markdown sustainability report",
            data=markdown_report.encode("utf-8"),
            file_name=f"sustainability_report_{selected_month}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.markdown("#### Method notes")
        st.write("- Raw kWh = watts × quantity × hours/day × days/month ÷ 1000.")
        st.write("- Calibration reconciles room allocations with each block's meter total.")
        st.write("- Confidence uses calibration closeness and schedule completeness.")
        st.write("- Carbon = calibrated kWh × editable emission factor.")
        st.write("- Scenario and waste figures are explicitly labelled modelled estimates / rule-based previews.")

st.divider()
st.caption("Campus Energy Estimation and Sustainability Analytics · Minor Project prototype · Synthetic sample data are for demonstration only.")
