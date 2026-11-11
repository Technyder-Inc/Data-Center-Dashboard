# Handover walkthrough

1. Overview: read the KPIs and compare Earliest Site Constraint with the portfolio aggregate; switch the chart between Power, Cooling and Racks.
2. Sidebar: navigate pages, change the horizon and growth, and click Quick Scenarios. The Infrastructure Expansion dropdown picks a resource (power, cooling or racks); facility, amount and activation month then appear. Add to plan appends an expansion, so several facilities can be planned together, each with a remove button. A one-line note reports the capacity added and whether the first exhaustion moved (Reset to Baseline is on Scenario Planning). The active growth mode is shown below the growth slider; dataset rates vary by site until an override is selected.
3. Capacity Forecasting: Edit facility data (modal) changes the synthetic dataset for the session; select facilities, switch resource and chart view, review the first limiting resource and the monthly table.
4. Scenario Planning: Edit assumptions (modal) changes the formerly fixed model values; set growth, per-site overrides, expansion, efficiency, budget and thresholds; compare before/after and read warnings.
5. Executive Decisions: edit unit costs and budget, review ranking and funded/unfunded status and recommendations, download the four CSVs.
6. Code map: all calculations live in `models/`; `models/scenarios.py::run_scenario` is the single entry point used by every page.
