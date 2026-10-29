# Implementation requirements carried from the final SRS

- Python 3.10+, Streamlit, pandas, NumPy, Plotly and pytest.
- CSV data files only; no database server or authentication.
- Inputs: rooms.csv, appliances.csv, schedules.csv, meters.csv.
- Raw appliance kWh = watts × qty × hours/day × days/month ÷ 1000.
- Support proportional and weighted calibration.
- Confidence score = 100 × (0.6 × calibration closeness + 0.4 × schedule completeness).
- Carbon = calibrated kWh × editable emission factor.
- Scenario controls: AC hours, lighting watts, computer hours, operating days.
- Waste preview: room intensity and appliance-hour thresholds, labelled Major Project preview.
- Export calibrated room CSV and Markdown report.
- Sample data must be visibly labelled and room-level estimates must not be presented as actual measurements.
