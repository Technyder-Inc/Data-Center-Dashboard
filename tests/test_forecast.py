import numpy as np
import pandas as pd
import pytest

from models.forecast import (
    Expansion, ScenarioParams, aggregate_exhaustion, build_forecast, effective_growth_pct,
    portfolio_series, resource_analysis,
)
from utils.validation import ValidationError, validate_sites


def cell(fc, site, res, month, col):
    return fc[(fc.site_id == site) & (fc.resource == res) & (fc.month == month)][col].iloc[0]


def one_site(**over):
    row = dict(site_id="DC1", site_name="A", location="X", electrical_capacity_mw=10.0, electrical_demand_mw=5.0,
               cooling_capacity_mwe=10.0, cooling_demand_mwe=5.0, rack_capacity=100, occupied_racks=50,
               annual_growth_pct=0.0, planned_power_expansion_mw=0.0, planned_cooling_expansion_mwe=0.0,
               planned_additional_racks=0, expansion_activation_month=0, estimated_project_cost_usd_m=0.0)
    row.update(over)
    return pd.DataFrame([row])


def test_baseline_totals_and_utilization(sites):
    fc = build_forecast(sites, ScenarioParams())
    ps = portfolio_series(fc)
    p0 = ps[(ps.month == 0) & (ps.resource == "power")].iloc[0]
    assert p0.capacity == pytest.approx(45.0)
    assert p0.demand == pytest.approx(32.5)
    assert p0.utilization_pct == pytest.approx(100 * 32.5 / 45.0)
    assert len(sites) == 6 and list(sites.site_id) == [f"DC{i}" for i in range(1, 7)]


def test_compound_growth(sites):
    fc = build_forecast(sites, ScenarioParams())
    assert cell(fc, "DC3", "power", 12, "demand") == pytest.approx(8.0 * 1.18)
    assert cell(fc, "DC3", "power", 6, "demand") == pytest.approx(8.0 * 1.18 ** 0.5)
    assert cell(fc, "DC3", "power", 36, "demand") == pytest.approx(8.0 * 1.18 ** 3)


def test_weighted_not_averaged(sites):
    ps = portfolio_series(build_forecast(sites, ScenarioParams()))
    util = ps[(ps.month == 24) & (ps.resource == "power")].utilization_pct.iloc[0]
    fc = build_forecast(sites, ScenarioParams())
    site_utils = fc[(fc.month == 24) & (fc.resource == "power")].utilization_pct
    d = fc[(fc.month == 24) & (fc.resource == "power")]
    assert util == pytest.approx(100 * d.demand.sum() / d.capacity.sum())
    assert abs(util - site_utils.mean()) > 0.01


def test_monthly_generation(sites):
    fc = build_forecast(sites, ScenarioParams())
    assert fc.month.min() == 0 and fc.month.max() == 36
    assert len(fc) == 6 * 3 * 37
    assert set(fc.resource) == {"power", "cooling", "racks"}


def test_zero_growth_never_exhausts():
    s = one_site()
    p = ScenarioParams()
    fc = build_forecast(s, p)
    assert fc.demand.groupby(fc.resource).nunique().max() == 1
    ra = resource_analysis(fc, s, p)
    assert ra.first_exhaustion_month.isna().all()


def test_exactly_100_percent_is_not_exhaustion():
    s = one_site(electrical_demand_mw=10.0)
    ra = resource_analysis(build_forecast(s, ScenarioParams()), s, ScenarioParams())
    power = ra[ra.resource == "power"].iloc[0]
    assert power.peak_util_pct == pytest.approx(100.0)
    assert pd.isna(power.first_exhaustion_month)
    assert power.first_critical_month == 0


def test_immediate_constraint():
    s = one_site(electrical_demand_mw=11.0)
    assert validate_sites(s).warnings
    ra = resource_analysis(build_forecast(s, ScenarioParams()), s, ScenarioParams())
    assert ra[ra.resource == "power"].first_exhaustion_month.iloc[0] == 0


def test_site_specific_growth_and_override_convention(sites):
    p = ScenarioParams(growth_mode="adjust", growth_value_pct=2.0)
    g = effective_growth_pct(sites, p)
    assert g["DC1"] == 15 and g["DC3"] == 20
    p = ScenarioParams(growth_mode="override", growth_value_pct=25.0, site_growth_overrides={"DC2": 5.0})
    g = effective_growth_pct(sites, p)
    assert g["DC2"] == 5.0 and g["DC1"] == 25.0
    assert effective_growth_pct(sites, ScenarioParams())["DC4"] == 16


def test_exhaustion_detection_month(sites):
    p = ScenarioParams()
    ra = resource_analysis(build_forecast(sites, p), sites, p)
    row = ra[(ra.site_id == "DC3") & (ra.resource == "cooling")].iloc[0]
    assert row.first_exhaustion_month == 12  # 7.8 * 1.18 = 9.204 > 9.2


def test_horizon_limits_analysis(sites):
    p = ScenarioParams(horizon=6)
    ra = resource_analysis(build_forecast(sites, p), sites, p)
    assert ra.first_exhaustion_month.isna().all()
    assert ra.peak_month.max() <= 6


def test_cooling_and_rack_bottlenecks():
    s = one_site(cooling_capacity_mwe=5.2, annual_growth_pct=10.0)
    p = ScenarioParams()
    ra = resource_analysis(build_forecast(s, p), s, p)
    exh = ra.set_index("resource").first_exhaustion_month
    assert not pd.isna(exh["cooling"]) and pd.isna(exh["power"])
    s = one_site(rack_capacity=52, annual_growth_pct=10.0)
    ra = resource_analysis(build_forecast(s, p), s, p)
    assert not pd.isna(ra.set_index("resource").first_exhaustion_month["racks"])


def test_expansion_activation_timing():
    s = one_site(electrical_demand_mw=9.0, annual_growth_pct=20.0)
    p = ScenarioParams(expansions=(Expansion("DC1", power_mw=5.0, month=10),))
    fc = build_forecast(s, p)
    assert cell(fc, "DC1", "power", 9, "capacity") == 10.0
    assert cell(fc, "DC1", "power", 10, "capacity") == 15.0
    assert cell(fc, "DC1", "cooling", 10, "capacity") == 10.0
    ra = resource_analysis(fc, s, p)
    assert ra[ra.resource == "power"].first_exhaustion_month.iloc[0] == 7  # before activation


def test_portfolio_exhaustion_differs_from_site(sites):
    p = ScenarioParams()
    fc = build_forecast(sites, p)
    agg = aggregate_exhaustion(portfolio_series(fc), p.horizon)
    ra = resource_analysis(fc, sites, p)
    site_first = ra.first_exhaustion_month.dropna().min()
    agg_first = min(v for v in agg.values() if v is not None)
    assert site_first == 12 and agg_first == 25


def test_efficiency_reduces_all_demand(sites):
    fc0 = build_forecast(sites, ScenarioParams())
    fc1 = build_forecast(sites, ScenarioParams(efficiency_pct=10.0))
    assert np.allclose(fc1.demand, fc0.demand * 0.9)
    assert np.allclose(fc1.capacity, fc0.capacity)


def test_invalid_inputs_rejected(sites):
    bad = sites.copy()
    bad.loc[0, "electrical_capacity_mw"] = -1
    with pytest.raises(ValidationError):
        build_forecast(bad, ScenarioParams())
    bad = sites.copy()
    bad.loc[0, "occupied_racks"] = -5
    assert not validate_sites(bad).ok
    bad = sites.drop(columns=["rack_capacity"])
    assert not validate_sites(bad).ok
    with pytest.raises(ValidationError):
        build_forecast(sites, ScenarioParams(efficiency_pct=100))
    with pytest.raises(ValidationError):
        build_forecast(sites, ScenarioParams(expansions=(Expansion("DC1", power_mw=-1),)))
    with pytest.raises(ValidationError):
        build_forecast(sites, ScenarioParams(expansions=(Expansion("DC9", power_mw=1),)))
    with pytest.raises(ValidationError):
        build_forecast(sites, ScenarioParams(horizon=7))


def test_rack_overcapacity_is_warning_not_error():
    rep = validate_sites(one_site(occupied_racks=120))
    assert rep.ok and any("overcapacity" in w for w in rep.warnings)
