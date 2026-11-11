# Methodology

## Forecast

For each site and resource (power MW, cooling MWe, racks), months 0 to 36:

`demand(m) = baseline_demand x (1 - efficiency) x (1 + growth) ^ (m / 12)`

`capacity(m) = baseline_capacity + sum of expansions with activation_month <= m`

Expansion capacity is available from its activation month, not before. Rack demand is fractional (not rounded).

## Growth convention

Priority: site-specific override, then portfolio setting, then dataset site rate. The portfolio setting is one of: dataset rates, adjust every site by +/- points, or override every site with one rate. Presets reset all overrides, so nothing carries over between scenarios.

## Exhaustion, warning, risk

- Exhaustion: first month where demand strictly exceeds capacity. Exactly 100% is not exhaustion.
- Warning and critical thresholds (default 85% and 95%): first month utilization reaches them.
- Site risk over months 0 to horizon: Critical = exhaustion; High = peak at or above critical threshold; Medium = peak at or above warning threshold; Low otherwise.
- Portfolio risk: Critical = aggregate resource exhausted; High = at least one site exhausted; Medium = at least one site at warning; Low otherwise.
- Portfolio utilization = sum(demand) / sum(capacity). Site percentages are never averaged.
- First limiting resource: the resource with the earliest exhaustion (ties by higher peak utilization); if none exhausts, the highest-peak resource.
- Earliest site/resource constraint and aggregate portfolio exhaustion are computed separately and shown side by side. A site can fail while the portfolio aggregate has spare capacity.
- Analysis uses months 0 to the selected horizon. Forecast demand at 12, 24 and 36 months is always shown.

## Scenarios

- Baseline: original assumptions.
- High Growth: 25% annual growth for all sites.
- Infrastructure Expansion: default DC3 +4 MW, +4 MWe, +100 racks at month 12 (configurable).
- Efficiency Optimization: 10% demand reduction, applied equally to power, cooling and racks (documented simplification, not a real engineering claim).
- Budget-Constrained: planned projects ranked and funded within the budget remaining after any manual expansion.

Baseline metrics stay separate from scenario month-0 demand.

## Capital and prioritization

Cost = MW x power cost + MWe x cooling cost + racks x rack cost (illustrative USD millions, editable).

Score 0 to 100: timing urgency 35% (100 x (1 - exhaustion month / horizon)), peak utilization 25% ((peak% - 50) / 50, capped), risk level 15% (Low 0, Medium 40, High 70, Critical 100), resource fit 15% (project adds the limiting resource), cost 10% (cheaper scores higher). Ties break by site ID. Selection walks the ranking and funds each project that fits the remaining budget; the rest are Unfunded. Planned projects enter the forecast only when funding is enabled (Budget-Constrained). No ROI is inferred.

## Recommendations

Deterministic rules over modeled results: site/resource limits, site vs portfolio gap, expansion schedule (6-month lead time), unfunded projects, over-budget requests, up to 6 months of delay (capped at month 36), and a 10% efficiency what-if. Each cites modeled sites, months, percentages or costs. The efficiency what-if reports exhaustion for the same resource it names. Scheduling distinguishes beginning work from commissioning and flags unfunded candidates and projects that do not add the limiting resource.

Project after-effects are hypothetical evaluations of each candidate added to the manual expansions, including candidates not funded. Their headroom uses the limiting resource's unit. Returned scenario parameters preserve requested inputs separately from applied funded expansions, allowing results to be replayed without double-counting.

## Worked test case

DC3 cooling: baseline load 7.8 MWe, capacity 9.2 MWe, growth 18% a year. Demand at month m is 7.8 x 1.18^(m/12). At month 11 it is 9.078 MWe (below capacity). At month 12 it is 9.204 MWe, which exceeds 9.2, so exhaustion is month 12. Portfolio cooling is 32.3 MWe of load on 42.4 MWe of capacity at month 0 (76.2%), and aggregate cooling is first exceeded in month 25, 13 months after DC3. The automated tests assert these values.

## Display colours

Utilization values are shown green below 70%, amber from 70% up to the warning threshold (85% by default) and red at or above the warning threshold. Risk labels use red for Critical (dark red) and High, yellow for Medium and green for Low. The 70% start of the amber band is a display choice taken from the reference mockup and does not change any calculation.

## Input limits and validation

Every numeric input uses one table of limits (`LIMITS` in `utils/validation.py`). The input widgets, the facility editor grid, the assumptions editor and the server-side checks all read from it, so a value cannot be valid in one place and rejected in another.

| Input | Minimum | Maximum |
|---|---|---|
| Portfolio annual growth (%) | 0 | 60 |
| Site annual growth (%) | -50 | 100 |
| Growth adjustment (points) | -10 | 25 |
| Efficiency reduction (%) | 0 | 60 |
| Expansion power (MW) | 0 | 100 |
| Expansion cooling (MWe) | 0 | 100 |
| Expansion racks | 0 | 5000 |
| Activation month | 0 | 36 |
| Capital budget (USD millions) | 0 | 1000 |
| Warning threshold (%) | 50 | 99 |
| Critical threshold (%) | 51 | 100 |
| Cost per MW (USD millions) | 0 | 100 |
| Cost per MWe (USD millions) | 0 | 100 |
| Cost per rack (USD millions) | 0 | 5 |
| Facility electrical or cooling capacity | 0 | 500 |
| Facility electrical or cooling demand | 0 | 1000 |
| Facility rack capacity | 0 | 50000 |
| Facility occupied racks | 0 | 100000 |
| Project cost (USD millions) | 0 | 100000 |

How a bad value is handled:
- The browser blocks entries outside a field's range, and an out-of-range number field turns red with the message "Outside the allowed range: this value is not applied". The model keeps the last valid value.
- Facility capacities must be above zero. Rack counts, activation months and added racks must be whole numbers. Demand above capacity is allowed and modeled as overload (a warning, not an error).
- Warning must be below critical, and every number must be finite.
- If an out-of-range, non-numeric or non-finite value is ever found in stored input state, it is reset to its default at the start of the run and a warning lists what was reset.
- If a scenario still fails validation, the page shows "Invalid inputs" with the reason and a Reset to Baseline button.

## Immediate attention

A site whose first exhaustion falls in month 6 or earlier (or month 0 if it is already over capacity) gets a critical "requires immediate attention" recommendation citing the resource, month and planned activation month.

## Editable assumptions and facility data

Under Capacity Forecasting, Edit facility data opens a modal editor for the six facilities (names, capacities, demand, growth, planned expansion and activation month). Edits are validated like the CSV, project cost and risk status are recalculated, and the data source is recorded in the scenario export. Under Scenario Planning, Edit assumptions opens a modal for the values that were fixed in the code: High Growth and Efficiency rates, the Infrastructure Expansion preset, the ranking weights and risk scores, commissioning lead time, immediate-attention window, amber colour band and the what-if values. Both can be reset. Edits last for the session and are not saved to the dataset file.

## Limitations

Constant growth, no uncertainty, redundancy, lead-time variation or workload migration; cooling in synthetic MWe; costs illustrative.
