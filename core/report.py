"""Build a compact Markdown report for download."""
from __future__ import annotations
import pandas as pd


def build_markdown_report(
    room_results: pd.DataFrame,
    month: str,
    method: str,
    emission_factor: float,
    sample_data: bool,
) -> str:
    """Create a readable Markdown sustainability summary."""
    total_measured = room_results[["block", "measured_kwh"]].drop_duplicates()["measured_kwh"].sum(min_count=1)
    total_calibrated = room_results["calibrated_kwh"].sum()
    total_carbon = room_results["carbon_kg"].sum()
    data_label = "SAMPLE DATA — illustrative demonstration only" if sample_data else "USER-UPLOADED DATA"
    lines = [
        "# Campus Energy Estimation and Sustainability Analytics Report",
        "",
        f"**Data status:** {data_label}",
        f"**Month:** {month}",
        f"**Calibration method:** {method.title()}",
        f"**Emission factor:** {emission_factor:.3f} kg CO₂/kWh (editable assumption)",
        "",
        "## Summary",
        f"- Measured block electricity total: {total_measured:,.2f} kWh",
        f"- Calibrated room allocation total: {total_calibrated:,.2f} kWh",
        f"- Estimated carbon footprint: {total_carbon:,.2f} kg CO₂",
        "- Room-level electricity and carbon values are estimates, not direct room-meter readings.",
        "",
        "## Block summary",
        "",
        "| Block | Meter total (kWh) | Calibrated allocation (kWh) | Estimated CO₂ (kg) | Difference (kWh) |",
        "|---|---:|---:|---:|---:|",
    ]
    for block, group in room_results.groupby("block"):
        meter_values = group["measured_kwh"].dropna().unique()
        meter = float(meter_values[0]) if len(meter_values) else 0.0
        calibrated = float(group["calibrated_kwh"].sum())
        carbon = float(group["carbon_kg"].sum())
        lines.append(f"| {block} | {meter:,.2f} | {calibrated:,.2f} | {carbon:,.2f} | {calibrated - meter:,.6f} |")
    lines += [
        "",
        "## Room results",
        "",
        "| Room | Block | Type | Raw kWh | Calibrated kWh | Confidence | Label | CO₂ (kg) |",
        "|---|---|---|---:|---:|---:|---|---:|",
    ]
    for _, row in room_results.sort_values(["block", "room_id"]).iterrows():
        lines.append(
            f"| {row['room_id']} — {row['name']} | {row['block']} | {row['room_type']} | "
            f"{row['raw_kwh']:,.2f} | {row['calibrated_kwh']:,.2f} | {row['confidence_score']:.1f} | "
            f"{row['confidence_label']} | {row['carbon_kg']:,.2f} |"
        )
    lines += [
        "",
        "## Limitations",
        "",
        "- Sample data are synthetic and are included for demonstration.",
        "- Room-level estimates are reconciled to aggregate block readings; no room-level ground truth is available.",
        "- Carbon results depend on the selected emission factor.",
    ]
    return "\n".join(lines)
