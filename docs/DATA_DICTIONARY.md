# Data Dictionary: data/synthetic_sites.csv

All values are synthetic. Cooling is in synthetic MW-equivalent (MWe) units and is not a detailed thermodynamic model.

| Field | Unit | Description | Validation |
|---|---|---|---|
| site_id | text | DC1 to DC6 (prototype DC-A to DC-F) | unique |
| site_name | text | Fictional facility name | required |
| location | text | City, state | required |
| electrical_capacity_mw | MW | Installed electrical capacity | > 0 |
| electrical_demand_mw | MW | Current electrical demand | >= 0; above capacity is a warning (modeled overload) |
| cooling_capacity_mwe | MWe | Cooling capacity, MW-equivalent | > 0 |
| cooling_demand_mwe | MWe | Current cooling demand | >= 0; above capacity is a warning |
| rack_capacity | racks | Installed racks | whole number > 0 |
| occupied_racks | racks | Currently occupied racks | whole number >= 0; above capacity is an overcapacity warning |
| annual_growth_pct | % per year | Site compound demand growth | -50 to 100 |
| planned_power_expansion_mw | MW | Candidate project power added | >= 0 |
| planned_cooling_expansion_mwe | MWe | Candidate project cooling added | >= 0 |
| planned_additional_racks | racks | Candidate project racks added | whole number >= 0 |
| expansion_activation_month | month | Month planned capacity becomes available | whole number 0 to 36 |
| estimated_project_cost_usd_m | USD millions | Cost at default unit costs (9.0 per MW, 3.5 per MWe, 0.02 per rack); the app recomputes with current cost inputs | >= 0 |
| risk_status | label | Derived, not invented: baseline scenario, 24-month horizon, 85%/95% thresholds | derived by generator |

Export columns carry units in their names (for example `power_horizon_demand_MW`, `cost_usd_m`).
