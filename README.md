# Campus Energy Estimation and Sustainability Analytics

A Streamlit prototype for the Minor Project. It estimates room-level electricity use from appliance inventories and schedules, calibrates estimates to block-level meter readings, scores confidence, calculates carbon estimates, simulates what-if changes, and presents a rule-based waste-detection preview.

> **Sample-data warning:** The included CSVs are synthetic demonstration data, not actual Amity University readings. Room-level consumption values are estimates because the prototype has no room-level meter ground truth.

## Features

- Dashboard with block meter reconciliation, room allocation, carbon estimate and confidence distribution.
- Room-wise raw versus calibrated energy table and chart.
- Proportional and weighted calibration methods.
- Editable carbon emission factor.
- Scenario levers for AC hours, lighting watts, computer hours and operating days.
- Clearly labelled Major Project preview for room intensity and appliance operating-hour rules.
- CSV upload validation and CSV/Markdown export.
- Unit tests for formulas, calibration, confidence and scenario savings.

## Run on Windows

1. Install Python 3.11 (Python 3.10 or newer is required) and VS Code.
2. Extract this project folder and open it in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt in VS Code and run:

   ```bat
   .venv\Scripts\activate.bat
   ```

6. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Generate the example CSVs (they are already included, but this command recreates them deterministically):

   ```powershell
   python generate_data.py
   ```

8. Run the application:

   ```powershell
   python -m streamlit run app.py
   ```

9. Streamlit will show a local URL, usually `http://localhost:8501`. Open it in the browser.

## Run tests

```powershell
python -m pytest -q
```

## Project structure

```text
campus-energy-demo/
├── app.py
├── generate_data.py
├── requirements.txt
├── README.md
├── GUIDE.md
├── REQUIREMENTS.md
├── core/
│   ├── data_loader.py
│   ├── estimation.py
│   ├── calibration.py
│   ├── confidence.py
│   ├── carbon.py
│   ├── scenarios.py
│   ├── waste.py
│   └── report.py
├── data/
│   ├── rooms.csv
│   ├── appliances.csv
│   ├── schedules.csv
│   └── meters.csv
└── tests/
    └── test_core.py
```

## Demonstration checklist

1. Start on the Campus Dashboard and point out the SAMPLE DATA banner.
2. Change the month and compare each block's measured total with its calibrated room allocation.
3. Open Room Analysis and explain raw kWh versus calibrated kWh and the confidence score.
4. Open Scenario Simulator and change the sliders; savings should update immediately.
5. Open Waste Preview and explain that flags use rules, not a trained ML model.
6. Open Data & Exports and download the room CSV and Markdown report.

## Important calculation notes

- A missing appliance schedule is treated as zero operating hours and lowers completeness.
- If every raw estimate in a block is zero but its meter reading is positive, calibration raises a clear error. The input data cannot mathematically satisfy both constraints without an extra allocation assumption.
- The 0.82 kg CO₂/kWh default is an editable illustrative assumption from the SRS. For formal reporting, use a documented factor appropriate to the period being reported.
- Scenario results use each room's baseline calibration factor; they are what-if estimates, not future meter readings.
