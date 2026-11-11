import pytest

from models.forecast import Expansion, ScenarioParams
from models.scenarios import PRESETS, baseline_like, preset_params, run_scenario
from utils import exports


def test_five_presets_run(sites):
    assert len(PRESETS) == 5
    for n in PRESETS:
        assert run_scenario(sites, preset_params(n)).params.name == n


def test_high_growth_is_25_percent(sites):
    r = run_scenario(sites, preset_params("High Growth"))
    f = r.forecast
    got = f[(f.site_id == "DC3") & (f.resource == "power") & (f.month == 12)].demand.iloc[0]
    assert got == pytest.approx(sites.electrical_demand_mw.iloc[2] * 1.25)


def test_infrastructure_expansion_timing_and_gain(sites):
    r = run_scenario(sites, preset_params("Infrastructure Expansion"))
    f = r.forecast
    cap = f[(f.site_id == "DC3") & (f.resource == "cooling")].set_index("month").capacity
    assert cap[11] == pytest.approx(9.2) and cap[12] == pytest.approx(13.2)
    base = run_scenario(sites, preset_params("Baseline"))
    assert r.portfolio["cooling_horizon_capacity"] - base.portfolio["cooling_horizon_capacity"] == pytest.approx(4.0)
    assert r.portfolio["power_baseline_capacity"] == base.portfolio["power_baseline_capacity"]


def test_efficiency_ten_percent(sites):
    r = run_scenario(sites, preset_params("Efficiency Optimization"))
    b = run_scenario(sites, preset_params("Baseline"))
    assert r.portfolio["power_month0_demand"] == pytest.approx(0.9 * b.portfolio["power_month0_demand"])
    assert r.portfolio["power_baseline_demand"] == pytest.approx(b.portfolio["power_baseline_demand"])
    assert r.portfolio["earliest_month"] > b.portfolio["earliest_month"]


def test_switching_and_reset_have_no_carryover(sites):
    a = run_scenario(sites, preset_params("Efficiency Optimization", horizon=24))
    b = run_scenario(sites, preset_params("Baseline", horizon=24))
    c = run_scenario(sites, baseline_like(a.params))
    assert b.portfolio == c.portfolio
    assert b.params.efficiency_pct == 0 and not b.params.expansions and b.params.growth_mode == "site"
    assert a.params.efficiency_pct == 10


def test_budget_constrained_selection(sites):
    r = run_scenario(sites, preset_params("Budget-Constrained", budget_usd_m=100))
    pr = r.projects
    funded = pr[pr.funding_status == "Funded"]
    assert funded.cost_usd_m.sum() <= 100 + 1e-9
    assert list(pr.priority_rank) == sorted(pr.priority_rank)
    assert pr.priority_score.is_monotonic_decreasing
    assert len(funded) + (pr.funding_status == "Unfunded").sum() == 6
    assert r.funded_cost_usd_m == pytest.approx(funded.cost_usd_m.sum())
    assert any("cannot fund" in w for w in r.warnings)
    tiny = run_scenario(sites, preset_params("Budget-Constrained", budget_usd_m=0))
    assert (tiny.projects.funding_status == "Unfunded").all() and tiny.funded_cost_usd_m == 0


def test_unfunded_projects_not_in_forecast(sites):
    r = run_scenario(sites, preset_params("Budget-Constrained", budget_usd_m=0))
    b = run_scenario(sites, preset_params("Baseline"))
    assert r.portfolio["power_horizon_capacity"] == b.portfolio["power_horizon_capacity"]


def test_budget_flag_off_does_not_apply_projects(sites):
    r = run_scenario(sites, ScenarioParams(budget_usd_m=500))
    assert r.portfolio["power_horizon_capacity"] == 45.0 and r.funded_cost_usd_m == 0


def test_over_budget_manual_expansion_warns(sites):
    p = ScenarioParams(expansions=(Expansion("DC3", power_mw=10, cooling_mwe=10, racks=500, month=6),), budget_usd_m=50)
    r = run_scenario(sites, p)
    assert r.manual_cost_usd_m == pytest.approx(10 * 9 + 10 * 3.5 + 500 * 0.02)
    assert any("exceeds" in w for w in r.warnings)
    assert any("shortfall" in x["detail"] for x in r.recommendations)


def test_late_activation_warning(sites):
    p = ScenarioParams(expansions=(Expansion("DC3", cooling_mwe=4, month=20),))
    r = run_scenario(sites, p)
    assert any("after modeled exhaustion" in w for w in r.warnings)


def test_csv_exports_consistent_with_dashboard(sites):
    r = run_scenario(sites, preset_params("Infrastructure Expansion", horizon=24))
    fac = exports.facility_frame(r)
    assert len(fac) == 6
    assert fac["power_horizon_demand_MW"].sum() == pytest.approx(r.portfolio["power_horizon_demand"])
    fc = exports.forecast_frame(r)
    assert len(fc) == 6 * 3 * 37 and set(fc.columns) >= {"unit", "utilization_pct", "month"}
    sc = exports.scenario_frame(r).set_index("parameter")
    assert float(sc.at["power_horizon_utilization", "value"]) == pytest.approx(r.portfolio["power_horizon_util_pct"])
    assert sc.at["earliest_constraint_site", "value"] == r.portfolio["earliest_site"]
    cap = exports.capital_frame(r)
    assert cap.cost_usd_m.sum() == pytest.approx(r.manual_cost_usd_m + r.projects.cost_usd_m.sum())
    for kind in ("facility", "forecast", "scenario", "capital"):
        assert exports.filename(r, kind) == f"capacity_{kind}_infrastructure_expansion_24m.csv"
    assert exports.to_csv_bytes(fac).startswith(b"scenario,")
