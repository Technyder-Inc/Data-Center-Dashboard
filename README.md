# Six-Site Data Center Capacity Planning and Executive Decision Simulator

Synthetic, public-safe Streamlit demonstration of regional data center capacity planning: monthly 36-month forecasts of power, cooling and rack capacity across six fictional sites, five scenarios, capital prioritization, deterministic recommendations and CSV exports. The app shows "Synthetic Data - Demonstration Only" on every page.

## Features

- Executive Overview: KPI cards, portfolio demand vs capacity chart, utilization donut, insights, six-site table, top recommendations.
- Capacity Forecasting: per-site and multi-site power, cooling and rack forecasts with threshold, exhaustion and expansion markers; first limiting resource per site; monthly table.
- Scenario Planning: horizon, growth (site rates, portfolio adjustment or override, per-site overrides), expansion, efficiency, budget, thresholds; before/after comparison; Reset to Baseline.
- Executive Decisions: cost assumptions, budget use, transparent project ranking, funded vs unfunded projects, recommendations, four CSV downloads.
- Site-level and portfolio-level exhaustion are reported separately everywhere.

## Structure

```
app.py                 sidebar navigation and controls, shared scenario run
pages/                 four page modules (render functions)
models/                forecast.py, scenarios.py, risk.py, capital.py (single calculation engine)
components/            charts.py, kpi_cards.py, styles.py, state.py (session state)
utils/                 validation.py, exports.py
data/synthetic_sites.csv
scripts/generate_data.py
tests/                 pytest suite
docs/                  DATA_DICTIONARY.md, METHODOLOGY.md, HANDOVER.md
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Data generation

```bash
python scripts/generate_data.py
```

Baseline figures come from the original prototype (DC-A to DC-F renamed DC1 to DC6: 45.0 MW capacity, 32.5 MW demand). Planned expansions use a seeded RNG (seed 20240601), so the CSV reproduces exactly. The screenshot's 24.0 MW dataset was a visual reference only; no KPI values were copied from it.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repository (root contains `app.py` and `requirements.txt`).
2. At https://share.streamlit.io choose New app, select the repo and branch, set main file `app.py`, then Deploy.
3. No secrets or environment variables are required. Python 3.11+.

Publishing has not been performed from this workspace.

## Third-party licences

| Package | Use | Licence |
|---|---|---|
| Streamlit | App framework | Apache 2.0 |
| pandas | Data handling | BSD 3-Clause |
| NumPy | Numerical calculations | BSD 3-Clause |
| Plotly | Charts | MIT |
| pytest (development only) | Tests | MIT |

No templates, fonts, images or other third-party assets are bundled.

## Assumptions and limitations

See [docs/METHODOLOGY.md](docs/METHODOLOGY.md). Cooling uses synthetic MW-equivalent units, not a thermodynamic model. Efficiency reduces power, cooling and rack demand by the same factor. Growth is constant and compound, with no uncertainty. Costs are illustrative and no ROI is inferred. Analysis covers months 0 to the selected horizon.
