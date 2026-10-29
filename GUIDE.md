# Demo Guide — What to click and what to explain

## 1. Start the app

Run `python -m streamlit run app.py` from the project root. Keep the terminal open while demonstrating. The browser tab is the frontend; the terminal runs the Python app.

## 2. Dashboard

**Say:** “The system starts with room inventory, appliance wattage and usage schedules. Raw estimates are calculated from those inputs. Since a campus usually has only block-level meter readings, calibration distributes the measured block total across the rooms. The check confirms that each block's room allocations sum to its meter total.”

Point to the Sample Data banner and clarify that the numbers are synthetic.

## 3. Room analysis

**Say:** “Raw kWh comes directly from the appliance formula. Calibrated kWh is adjusted to match the block meter. Confidence is a heuristic based on how much calibration changed the raw estimate and how complete the appliance schedules are.”

## 4. Scenario simulator

Move one or more sliders. **Say:** “This is a what-if model. It estimates savings from lower appliance usage using the baseline calibration factor. These are not actual measured savings.”

## 5. Waste preview

**Say:** “This preview has two transparent rules: unusually high kWh per square metre compared with rooms of the same type, and appliance operating hours above a configurable threshold. It is a rule-based preview, not a trained AI model, and is reserved for the Major Project scope.”

## 6. Data and exports

Download the calibrated room CSV and Markdown sustainability report. Explain that uploaded files must follow the four required schemas, and that the prototype has no database server.

## Questions you may be asked

**Why are there no smart meters in each room?** The methodology is designed to use an appliance inventory and operating schedules, reconciled to available block-level measurements.

**Are room-level results actual measurements?** No. They are estimates because no room-level ground-truth readings are available.

**Why calibrate?** A raw bottom-up estimate may not match the block's meter. Calibration makes the room allocations sum to that measured block total.

**Is waste detection AI/ML?** Not in this minor-project prototype. The preview is rule-based; advanced prediction is future Major Project scope.

**Why is the carbon factor editable?** Emissions depend on the factor selected for the relevant electricity reporting period. The default is an illustrative assumption, not a claim of measured emissions.
