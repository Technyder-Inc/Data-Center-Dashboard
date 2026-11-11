# SOW reconciliation and delivery readiness

Date: 11 November 2026. Scope: the Six-Site Data Center Capacity Planning and Executive Decision Simulator, checked against the client Statement of Work (SOW v1.0, November 2026). This replaces the earlier report, which was written without the SOW.

## 1. Result

**Not ready for final acceptance.** Every functional and technical SOW requirement is implemented and was verified locally. Two delivery items cannot be satisfied from this workspace: the public Streamlit deployment and the recorded walkthrough or live session. The project owner has accepted the two deliberate deviations in section 5; written client confirmation is still advisable.

## 2. SOW compliance matrix

Status key: VERIFIED = implemented and checked by automated test, browser run or both. IMPLEMENTED = present in code, checked by inspection only. INCOMPLETE = not satisfied. UNVERIFIED = cannot be checked here.

### Section 2 and 4: functional requirements

| SOW item | Status | Evidence |
|---|---|---|
| M1 KPIs: capacity, demand, utilization, headroom (MW) | VERIFIED | Overview cards and resource table; model tests; browser text check |
| M1 cooling capacity and utilization, rack capacity and occupied racks | VERIFIED | Overview "Current Resource Capacity and Headroom" table |
| M1 forecast demand at 12, 24, 36 months | VERIFIED | Overview chips |
| M1 facilities approaching constraints, earliest site exhaustion, portfolio risk | VERIFIED | Overview chips and fifth KPI card; risk tests |
| M1 charts: demand vs capacity, power utilization, six-site table, risk indicators, insights and actions | VERIFIED | Overview page rendered in Chrome |
| M1 metrics recalculate when parameters change | VERIFIED | Sidebar quick scenarios clicked in Chrome; app tests |
| M2 six sites DC1 to DC6 with all listed fields | VERIFIED | `data/synthetic_sites.csv`; dataset tests; new "Facility Data and Planned Expansion" table |
| M2 select and compare facilities (utilization, forecasts, constraints, expansion) | VERIFIED | Forecasting page facility selector, charts, constraint table, facility and expansion table |
| M2 risk status Low, Medium, High, Critical | VERIFIED | Risk classification tests |
| M3 horizons 6, 12, 18, 24, 30, 36 and monthly calculation | VERIFIED | Horizon selector; forecast tests |
| M3 compound and site-specific growth, expansion activation, thresholds | VERIFIED | Forecast and scenario tests |
| M3 power, cooling, rack constraints and first limiting resource | VERIFIED | Resource-specific exhaustion tests |
| M3 baseline distinguishable from projections | VERIFIED | Baseline vs projected table; separate baseline columns |
| M4 sidebar controls: all nine inputs | VERIFIED | Sidebar (horizon, growth, expansion) plus Scenario Planning (site growth, power, cooling, racks, activation month, efficiency, budget, thresholds) |
| M4 five predefined scenarios and Reset to Baseline | VERIFIED | Model tests, app tests, Chrome clicks |
| M4 updates KPIs, charts, risks, recommendations with no reload | VERIFIED | Chrome run; app tests |
| M5 configurable unit costs, project cost, budget vs proposed, timing, capacity gained, post-investment headroom | VERIFIED | Executive Decisions page; capital tests |
| M5 transparent ranking on urgency, risk, cost; no ROI claims | VERIFIED | Documented weights; ranking tests; visible disclaimer |
| M6 recommendations: at-risk sites, expansion timing, immediate attention, optimization, over-budget, cost of deferral | VERIFIED | Rule-based recommendations. The "immediate attention" rule was missing and was added in this pass (section 4) |
| M6 each recommendation cites modeled metrics; deterministic rules | VERIFIED | Recommendation tests; no AI or LLM calls |
| M7 four CSV downloads | VERIFIED | All four downloaded in Chrome; export tests compare to dashboard values |
| M7 printable summary | Optional | Not built, as the SOW allows |

### Section 3, 5, 6, 7: technology, design, calculations, nonfunctional

| SOW item | Status | Evidence |
|---|---|---|
| Python 3.11+, Streamlit, pandas, NumPy, Plotly, CSV data | VERIFIED | `requirements.txt`; no other runtime libraries |
| No paid API, database or backend | VERIFIED | Source and dependency review |
| Dark navy theme, status colors, KPI cards, Plotly charts, sidebar navigation | VERIFIED | Chrome screenshots against the reference mockup |
| Four navigation pages | VERIFIED | Opened in Chrome after every scenario |
| Utilization, headroom, compound growth, exhaustion, weighted portfolio utilization formulas | VERIFIED | Calculation tests, including worked DC3 case (docs/METHODOLOGY.md) |
| Cooling, rack, cost and risk calculations documented | VERIFIED | docs/METHODOLOGY.md, docs/DATA_DICTIONARY.md |
| Portfolio exhaustion does not hide earlier site constraint; earliest site/resource shown prominently | VERIFIED | DC3 cooling month 12 vs aggregate cooling month 25; tests and Overview card |
| Synthetic dataset reproducible, generator script | VERIFIED | `scripts/generate_data.py`; round-trip test |
| Clear errors for invalid inputs; no negative or inconsistent inputs accepted | VERIFIED | Validation tests, including non-finite values |
| Consistency across pages | VERIFIED | One `run_scenario` entry point feeds all pages; cross-page tests |
| Responds promptly | VERIFIED | Annual Demand Growth slider steps measured at 0.3 to 0.5 s end to end in Chrome on all four pages, after caching and a faster calculation path were added in this pass (a step took about 1.5 s before) |
| Visible "Synthetic Data" notice | VERIFIED, deviation | On every page; wording uses a hyphen (section 5) |
| No login, no credentials, no proprietary data | VERIFIED | Source and data scan |
| Modular, documented code | VERIFIED | models, components, pages, utils, scripts |
| Third-party licences documented (section 13) | VERIFIED | Added to README in this pass |

### Section 8: deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| 1 Source code | VERIFIED | Complete in this folder |
| 2 requirements.txt | VERIFIED | `streamlit>=1.49,<2`, pandas, NumPy, Plotly; tested on Streamlit 1.49.1 and 1.67.0 |
| 3 Dataset and generation script | VERIFIED | See above |
| 4 Forecast and scenario modules | VERIFIED | `models/` |
| 5 Dashboard, four pages | VERIFIED | See above |
| 6 Capital planning module | VERIFIED | `models/capital.py` |
| 7 Export functionality | VERIFIED | See above |
| 8 GitHub repository | VERIFIED | Latest code pushed to the `main` branch of the repository in section 7 |
| 9 Streamlit Community Cloud deployment | INCOMPLETE | Not deployed; no public URL |
| 10 README | VERIFIED | Installation, local run, data generation, tests, deployment, limitations, licences |
| 11 Data dictionary and methodology | VERIFIED | docs/ |
| 12 Automated tests | VERIFIED | 70 tests; 18 SOW-listed behaviors covered |
| 13 Recorded walkthrough or live session | INCOMPLETE | Cannot be produced here; written walkthrough outline is in docs/HANDOVER.md |
| 14 Acceptance-test defects resolved | VERIFIED locally | No open critical or high defects found |

### Section 9: final acceptance criteria

| Criterion | Status |
|---|---|
| Six facilities represented correctly | VERIFIED |
| Four pages functional | VERIFIED |
| Input changes reflected consistently | VERIFIED |
| Forecasts verified against documented test cases | VERIFIED |
| Earliest site constraints identified | VERIFIED |
| Validation of physical inputs | VERIFIED |
| All CSV exports working | VERIFIED |
| Public Streamlit deployment operational | INCOMPLETE |
| Complete source delivered | VERIFIED (pushed to GitHub) |
| No unresolved critical or high defects | VERIFIED locally |

## 3. Mandatory gaps found against the SOW

1. Module 2: no screen showed the per-facility synthetic fields, planned expansion capacity, cost and activation month together.
2. Module 6: no rule for "sites requiring immediate attention".
3. Section 13: third-party licences were not documented.
4. Section 7: changing the Annual Demand Growth slider took about 1.5 s per step. Every rerun recalculated the five-preset comparison and the baseline, and each scenario run re-validated its inputs and used slow per-site lookups.
5. Section 8: the deployment and the recorded walkthrough remain open. The GitHub push was completed after this audit (section 7).

## 4. Defects fixed in this pass

Items 1 to 4 above were fixed: a facility data table on Capacity Forecasting, an immediate-attention recommendation (first exhaustion within 6 months, stated in the methodology), a licence table in the README, and a performance fix for the growth slider: the preset comparison is computed only on the pages that show it and is cached on the inputs it depends on, the baseline run is cached, repeated input validation is skipped inside a run, and the per-site analysis is vectorized. One scenario run fell from 0.25 s to 0.11 s and a slider step now takes 0.3 to 0.5 s. A methodology worked case (DC3 cooling) and two tests were added. An inline import was moved to the top of its module. The earlier independent audit also fixed double-counted funded projects, resource-specific recommendation text, strict exhaustion comparison, non-finite input validation, export unit columns and an empty-export header; those fixes are retained.

## 5. Deliberate deviations

Both were accepted by the project owner on 11 November 2026.

1. The SOW notice reads "Synthetic Data - Demonstration Only" with a plain hyphen instead of the SOW's em dash, because of the developer's no-em-dash style rule. Wording and visibility are otherwise as required.
2. The Executive Overview follows the supplied mockup, then adds a chips row and a three-resource capacity table, because the SOW lists KPIs (cooling, racks, headroom, 12 and 24 month demand, portfolio risk) that the mockup does not show. These extra rows are the only departure from the mockup layout.

## 6. Tests and smoke checks executed

- `python -m pytest -q`: 70 passed (about 14 s; it took about 38 s before the performance fix).
- `python -m ruff check .`: all checks passed.
- Application started on Streamlit 1.49.1; health endpoint returned 200.
- Chrome: all four pages opened after each of four quick scenarios, no exceptions, sidebar fixed at 290 px, still visible after reload.
- Chrome slider timing: six consecutive Annual Demand Growth steps on each page took 0.3 to 0.6 s including a fixed 0.12 s wait, with no exceptions.
- Chrome text check: every required control, panel and notice found on all four pages.
- Chrome download check on the previous pass: four CSVs delivered (facility 6 rows, forecast 666 rows, scenario 49 rows, capital 6 rows).
- Clean-environment install on Streamlit 1.67.0 passed in the previous audit pass (67 model and export tests and 2 app tests).

## 7. GitHub readiness

Repository: https://github.com/unixkid/Data-Center-Dashboard (public, branch `main`). The first version was pushed earlier, and the audit fixes, tests and this report were pushed on 11 November 2026 (see `git log`). Logs and `docs/audit-evidence/` are ignored. Before pushing, the staged files were scanned: no credentials, binaries or non-ASCII characters, lint clean, 70 tests passing.

## 8. Deployment readiness

Ready to deploy; not deployed. No secrets or environment variables are needed. Steps for the repository owner:

1. Open https://share.streamlit.io and sign in with the GitHub account that owns the repository.
2. Choose New app, select `unixkid/Data-Center-Dashboard`, branch `main`, main file `app.py`.
3. Deploy, open the public URL, and run the check list in docs/HANDOVER.md.
4. Record the URL in the README.

No deployment is claimed until a working public URL has been opened and checked.

## 9. Remaining client actions

1. Deploy under the owning GitHub and Streamlit accounts and share the public URL.
2. Schedule or approve the recorded walkthrough or live knowledge-transfer session.
3. Run the final acceptance check on the public URL.
4. Optionally confirm the two section 5 deviations with the client in writing.

## 10. Final acceptance recommendation

**Not ready to mark fully delivered.** The application meets every functional, calculation, export, validation, documentation and testing requirement in the SOW, with no known critical or high defects. Final acceptance also requires a public deployment and a walkthrough session, and neither exists yet. Once the app is deployed with a working URL and the walkthrough is delivered, the project is ready for acceptance.
