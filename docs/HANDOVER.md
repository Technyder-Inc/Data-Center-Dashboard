# Handover walkthrough

1. Overview: read the KPIs and compare Earliest Site Constraint with the portfolio aggregate; switch the chart between Power, Cooling and Racks.
2. Top-right control bar: navigate pages, change the horizon, growth and expansion, and click Quick Scenarios (Reset to Baseline is on Scenario Planning).
3. Capacity Forecasting: select facilities, switch resource and chart view, review the first limiting resource and the monthly table.
4. Scenario Planning: set growth, per-site overrides, expansion, efficiency, budget and thresholds; compare before/after and read warnings.
5. Executive Decisions: edit unit costs and budget, review ranking and funded/unfunded status and recommendations, download the four CSVs.
6. Code map: all calculations live in `models/`; `models/scenarios.py::run_scenario` is the single entry point used by every page.
