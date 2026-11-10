import pytest

from models.forecast import ScenarioParams
from models.risk import classify_risk
from models.scenarios import PRESETS, preset_params, run_scenario


def test_classification_boundaries():
    assert classify_risk(84.9, None, 85, 95) == "Low"
    assert classify_risk(85.0, None, 85, 95) == "Medium"
    assert classify_risk(95.0, None, 85, 95) == "High"
    assert classify_risk(100.0, None, 85, 95) == "High"
    assert classify_risk(100.1, 12, 85, 95) == "Critical"


def test_site_risk_and_earliest_constraint(sites):
    r = run_scenario(sites, preset_params("Baseline"))
    pf = r.portfolio
    assert (pf["earliest_site"], pf["earliest_resource"], pf["earliest_month"]) == ("DC3", "cooling", 12)
    assert pf["aggregate_month"] == 25 and pf["site_lead_months"] == 13
    ss = r.site_summary.set_index("site_id")
    assert ss.at["DC3", "risk_level"] == "Critical"
    assert ss.at["DC6", "risk_level"] == "Medium"
    assert pf["sites_exhausted"] == int(ss.earliest_exhaustion_month.notna().sum()) == 4
    assert pf["portfolio_risk"] == "Critical"


def test_portfolio_not_misreported_when_aggregate_ok(sites):
    r = run_scenario(sites, preset_params("Budget-Constrained"))
    assert r.portfolio["aggregate_month"] is None
    assert r.portfolio["earliest_month"] == 12
    assert r.portfolio["portfolio_risk"] == "High"


def test_thresholds_configurable(sites):
    lo = run_scenario(sites, ScenarioParams(horizon=6, warn_pct=70, critical_pct=80))
    hi = run_scenario(sites, ScenarioParams(horizon=6, warn_pct=95, critical_pct=99))
    assert lo.portfolio["sites_approaching"] > hi.portfolio["sites_approaching"]


def test_recommendations_cite_modeled_values(sites):
    r = run_scenario(sites, preset_params("Baseline"))
    top = r.recommendations[0]
    assert "DC3" in top["title"] and "month 12" in top["detail"]
    assert all(x["detail"] for x in r.recommendations)
    assert [x["priority"] for x in r.recommendations] == list(range(1, len(r.recommendations) + 1))


def test_no_contradictory_kpis_across_scenarios(sites):
    for name in PRESETS:
        r = run_scenario(sites, preset_params(name))
        pf, ss = r.portfolio, r.site_summary
        assert pf["power_month0_util_pct"] == pytest.approx(100 * pf["power_month0_demand"] / pf["power_month0_capacity"])
        assert pf["sites_exhausted"] <= pf["sites_approaching"] <= 6
        if pf["earliest_month"] is not None and pf["aggregate_month"] is not None:
            assert pf["earliest_month"] <= pf["aggregate_month"]
        exh = ss.earliest_exhaustion_month.dropna()
        if len(exh):
            assert pf["earliest_month"] == int(exh.min())
        else:
            assert pf["earliest_month"] is None
        assert (ss.risk_level == "Critical").sum() == pf["sites_exhausted"]
