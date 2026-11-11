"""Independent boundary calculations and regressions found during the audit."""
from dataclasses import replace
import io
import math

import pandas as pd
import pytest

from models.capital import CostAssumptions
from models.forecast import Expansion, ScenarioParams, build_forecast, resource_analysis
from models.scenarios import PRESETS, preset_params, run_scenario
from test_forecast import one_site
from utils import exports
from utils.validation import ValidationError


@pytest.mark.parametrize("resource,field", [("power", "electrical_demand_mw"),
                                           ("cooling", "cooling_demand_mwe"), ("racks", "occupied_racks")])
def test_each_resource_is_first_independently(resource, field):
    s = one_site(annual_growth_pct=20, **{field: 90 if resource == "racks" else 9})
    r = run_scenario(s, ScenarioParams())
    # 9 * 1.2**(6/12) < 10; 9 * 1.2**(7/12) > 10.
    assert 9 * math.sqrt(1.2) < 10 < 9 * 1.2 ** (7 / 12)
    assert r.portfolio["earliest_resource"] == resource
    assert r.portfolio["earliest_month"] == 7


def test_strict_exhaustion_and_preventive_expansion():
    tiny = one_site(electrical_demand_mw=10 + 1e-10)
    r = run_scenario(tiny, ScenarioParams())
    assert r.portfolio["earliest_month"] == 0
    s = one_site(electrical_demand_mw=9, annual_growth_pct=20)
    early = ScenarioParams(expansions=(Expansion("DC1", power_mw=6, month=7),))
    assert pd.isna(run_scenario(s, early).site_summary.power_exhaustion_month.iloc[0])
    late = replace(early, expansions=(Expansion("DC1", power_mw=6, month=8),))
    assert run_scenario(s, late).site_summary.power_exhaustion_month.iloc[0] == 7


def test_weighted_headroom_with_local_cooling_overload():
    s = pd.concat([one_site(cooling_demand_mwe=11), one_site(site_id="DC2", electrical_capacity_mw=90)], ignore_index=True)
    r = run_scenario(s, ScenarioParams())
    assert r.portfolio["power_month0_util_pct"] == 10
    assert r.portfolio["power_month0_headroom"] == 90
    assert (r.portfolio["earliest_site"], r.portfolio["earliest_resource"], r.portfolio["earliest_month"]) == ("DC1", "cooling", 0)
    assert r.portfolio["aggregate_month"] is None


@pytest.mark.parametrize("params", [ScenarioParams(growth_mode="adjust", growth_value_pct=-200),
    ScenarioParams(growth_mode="adjust", growth_value_pct=float("nan")),
    ScenarioParams(budget_usd_m=float("nan")),
    ScenarioParams(expansions=(Expansion("DC1", power_mw=float("inf")),)),
    ScenarioParams(expansions=(Expansion("DC1", racks=1.5),)),
    ScenarioParams(expansions=(Expansion("DC1", month=1.5),))])
def test_invalid_scenario_rejected(params):
    with pytest.raises(ValidationError):
        run_scenario(one_site(), params)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_invalid_cost_rejected(value):
    with pytest.raises(ValidationError):
        run_scenario(one_site(), ScenarioParams(), CostAssumptions(power_per_mw_usd_m=value))


def test_nonfinite_dataset_rejected():
    with pytest.raises(ValidationError):
        build_forecast(one_site(electrical_capacity_mw=float("inf")), ScenarioParams())


def test_limiting_peak_is_not_unrelated_resource_peak():
    s = one_site(electrical_demand_mw=11, cooling_demand_mwe=9, annual_growth_pct=20)
    p = ScenarioParams(expansions=(Expansion("DC1", power_mw=20, month=1),))
    r = run_scenario(s, p)
    rec = next(x for x in r.recommendations if x["site_id"] == "DC1" and "Power demand" in x["detail"])
    assert "power peak 110.0%" in rec["detail"]
    assert r.site_summary.peak_resource.iloc[0] == "cooling"


def test_delay_reports_actual_clamped_months():
    r = run_scenario(one_site(electrical_demand_mw=11),
                     ScenarioParams(expansions=(Expansion("DC1", power_mw=5, month=34),)))
    rec = next(x for x in r.recommendations if x["title"] == "Impact of delaying investment")
    assert "2 months (month 34 to 36)" in rec["detail"]


def test_efficiency_changes_first_limiting_resource():
    s = one_site(electrical_demand_mw=9.9, cooling_demand_mwe=9.5, annual_growth_pct=20)
    p = ScenarioParams(expansions=(Expansion("DC1", power_mw=10, month=3),))
    assert run_scenario(s, p).portfolio["earliest_resource"] == "power"
    r = run_scenario(s, replace(p, efficiency_pct=10))
    assert r.portfolio["earliest_resource"] == "cooling"
    # The efficiency recommendation must describe the original resource, not cooling's date.
    rec = next(x for x in run_scenario(s, p).recommendations if x["title"] == "Capacity optimization opportunity")
    assert "no exhaustion within the horizon" in rec["detail"]


def test_funded_scenario_inputs_are_replayable(sites):
    r = run_scenario(sites, preset_params("Budget-Constrained"))
    replay = run_scenario(sites, r.params, r.costs)
    pd.testing.assert_frame_equal(r.forecast, replay.forecast)
    assert replay.total_investment_usd_m == r.total_investment_usd_m


@pytest.mark.parametrize("name", PRESETS)
def test_all_exports_roundtrip_active_scenario(sites, name):
    r = run_scenario(sites, preset_params(name))
    for fn in (exports.facility_frame, exports.forecast_frame, exports.scenario_frame, exports.capital_frame):
        frame = fn(r)
        parsed = pd.read_csv(io.BytesIO(exports.to_csv_bytes(frame)))
        assert len(parsed) == len(frame)
        assert parsed.scenario.eq(name).all()
    fc = exports.forecast_frame(r)
    assert not fc.duplicated(["site_id", "resource", "month"]).any()
    assert fc.demand_units.notna().all() and fc.capacity_units.notna().all()
    # Independently check all 666 monthly demands using scalar Python arithmetic.
    for row in r.sites.itertuples():
        growth = 25 if name == "High Growth" else row.annual_growth_pct
        factor = .9 if name == "Efficiency Optimization" else 1
        for res, demand in [("power", row.electrical_demand_mw), ("cooling", row.cooling_demand_mwe), ("racks", row.occupied_racks)]:
            actual = fc[(fc.site_id == row.site_id) & (fc.resource == res)].set_index("month")
            for month in range(37):
                assert actual.at[month, "demand_units"] == pytest.approx(demand * factor * math.pow(1 + growth / 100, month / 12))


def test_resource_exhaustion_expected_month_from_logs():
    s = one_site(cooling_demand_mwe=8, annual_growth_pct=25)
    p = ScenarioParams()
    a = resource_analysis(build_forecast(s, p), s, p).set_index("resource")
    expected = math.floor(12 * math.log(10 / 8) / math.log(1.25)) + 1
    assert expected == 13
    assert a.at["cooling", "first_exhaustion_month"] == expected


def test_empty_capital_export_has_headers():
    r = run_scenario(one_site(), ScenarioParams())
    out = pd.read_csv(io.BytesIO(exports.to_csv_bytes(exports.capital_frame(r))))
    assert out.empty and "cost_usd_m" in out.columns


def test_methodology_worked_case_and_immediate_attention(sites):
    import pytest
    from models.forecast import ScenarioParams
    from models.scenarios import run_scenario
    assert 7.8 * 1.18 ** (11 / 12) == pytest.approx(9.078, abs=1e-3)
    assert 7.8 * 1.18 > 9.2
    base = run_scenario(sites, ScenarioParams())
    assert not [x for x in base.recommendations if "immediate attention" in x["title"]]
    hot = run_scenario(sites, ScenarioParams(growth_mode="override", growth_value_pct=45.0))
    imm = [x for x in hot.recommendations if "immediate attention" in x["title"]]
    assert imm and imm[0]["severity"] == "critical" and imm[0]["month"] <= 6


def test_expansion_impact_and_multiple_expansions(sites):
    from components import state
    from models.forecast import Expansion, ScenarioParams
    from models.scenarios import baseline_like, run_scenario
    base = run_scenario(sites, ScenarioParams())
    power = run_scenario(sites, ScenarioParams(expansions=(Expansion("DC3", power_mw=1.0, month=0),)))
    note = state.expansion_impact(power, base)
    assert "+1 MW" in note and "stays month 12" in note and "first limit is cooling" in note
    cooling = run_scenario(sites, ScenarioParams(expansions=(Expansion("DC3", cooling_mwe=4.0, month=0),)))
    note = state.expansion_impact(cooling, base)
    assert "+4 MWe" in note and "moves from month 12" in note
    both = run_scenario(sites, ScenarioParams(expansions=(Expansion("DC3", cooling_mwe=4.0, month=0), Expansion("DC4", power_mw=2.0, month=0))))
    note = state.expansion_impact(both, base)
    assert "2 expansions" in note and "DC3, DC4" in note and "+2 MW" in note and "+4 MWe" in note
    other = run_scenario(sites, ScenarioParams(expansions=(Expansion("DC1", power_mw=2.0, month=0),)))
    assert "No expansion targets DC3" in state.expansion_impact(other, base)
    assert state.expansion_impact(base, baseline_like(base.params)) is None
