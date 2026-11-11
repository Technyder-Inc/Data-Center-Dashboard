import pytest
from dataclasses import replace

from models.assumptions import DEFAULT_ASSUMPTIONS, Assumptions, validate_assumptions
from models.editing import EDITABLE_COLUMNS, apply_site_edits
from models.forecast import ScenarioParams
from models.scenarios import preset_params, run_scenario
from utils import exports

IDS = ["DC1", "DC2", "DC3", "DC4", "DC5", "DC6"]


def test_defaults_reproduce_original_behaviour(sites):
    a = run_scenario(sites, preset_params("Budget-Constrained"))
    b = run_scenario(sites, preset_params("Budget-Constrained", assumptions=DEFAULT_ASSUMPTIONS), assumptions=DEFAULT_ASSUMPTIONS)
    assert a.portfolio == b.portfolio and list(a.projects.site_id) == list(b.projects.site_id)
    assert validate_assumptions(DEFAULT_ASSUMPTIONS, IDS) == []


def test_assumption_validation():
    bad = [replace(DEFAULT_ASSUMPTIONS, weight_cost=20.0), replace(DEFAULT_ASSUMPTIONS, high_growth_pct=-1),
           replace(DEFAULT_ASSUMPTIONS, efficiency_pct=80), replace(DEFAULT_ASSUMPTIONS, expansion_site="DC9"),
           replace(DEFAULT_ASSUMPTIONS, score_medium=90), replace(DEFAULT_ASSUMPTIONS, lead_time_months=99),
           replace(DEFAULT_ASSUMPTIONS, caution_pct=float("nan"))]
    for a in bad:
        assert validate_assumptions(a, IDS), a


def test_edited_assumptions_change_presets_ranking_and_text(sites):
    a = Assumptions(high_growth_pct=30.0, efficiency_pct=15.0, expansion_site="DC4", expansion_power_mw=2.0, expansion_cooling_mwe=0.0,
                    expansion_racks=0, expansion_month=3)
    assert preset_params("High Growth", assumptions=a).growth_value_pct == 30.0
    assert preset_params("Efficiency Optimization", assumptions=a).efficiency_pct == 15.0
    e = preset_params("Infrastructure Expansion", assumptions=a).expansions[0]
    assert (e.site_id, e.power_mw, e.month) == ("DC4", 2.0, 3)
    cost_first = replace(DEFAULT_ASSUMPTIONS, weight_timing=0.0, weight_peak=0.0, weight_risk=0.0, weight_fit=0.0, weight_cost=100.0)
    r = run_scenario(sites, ScenarioParams(), assumptions=cost_first)
    assert list(r.projects.site_id)[0] == r.projects.sort_values("cost_usd_m").site_id.iloc[0]
    lead = run_scenario(sites, ScenarioParams(), assumptions=replace(DEFAULT_ASSUMPTIONS, lead_time_months=2))
    text = " ".join(x["detail"] for x in lead.recommendations)
    assert "2-month commissioning lead time" in text and "DC3 cooling: begin by month 10" in text


def edited_frame(sites, changes=None):
    df = sites[["site_id", *EDITABLE_COLUMNS]].copy()
    for (row, col), value in (changes or {}).items():
        df[col] = df[col].astype(float) if col not in ("site_id", "site_name", "location") else df[col]
        df.loc[row, col] = value
    return df


def test_site_edits_validate_recompute_and_flow_through(sites):
    ok, errors, warnings = apply_site_edits(sites, edited_frame(sites, {(2, "cooling_capacity_mwe"): 12.0, (2, "annual_growth_pct"): 10.0}))
    assert errors == [] and ok is not None
    assert ok.loc[2, "cooling_capacity_mwe"] == 12.0 and ok["site_id"].tolist() == IDS
    base = run_scenario(sites, ScenarioParams())
    edited = run_scenario(ok, ScenarioParams())
    assert edited.portfolio["earliest_month"] != base.portfolio["earliest_month"] or edited.portfolio["earliest_site"] != "DC3"
    assert edited.portfolio["cooling_baseline_capacity"] == pytest.approx(sites.cooling_capacity_mwe.sum() + 2.8)
    for bad in ({(0, "electrical_capacity_mw"): -1}, {(0, "electrical_capacity_mw"): 0}, {(1, "occupied_racks"): 1.5},
                {(1, "expansion_activation_month"): 50}, {(3, "annual_growth_pct"): 500}, {(4, "rack_capacity"): float("nan")}):
        none, errors, _ = apply_site_edits(sites, edited_frame(sites, bad))
        assert none is None and errors, bad
    over, errors, warnings = apply_site_edits(sites, edited_frame(sites, {(0, "occupied_racks"): 999}))
    assert errors == [] and any("overcapacity" in w for w in warnings)
    renamed = edited_frame(sites)
    renamed.loc[0, "site_id"] = "DC9"
    assert apply_site_edits(sites, renamed)[0] is None


def test_export_records_data_source_and_assumptions(sites):
    base = exports.scenario_frame(run_scenario(sites, ScenarioParams())).set_index("parameter")
    assert base.at["facility_data_source", "value"] == "data/synthetic_sites.csv"
    assert float(base.at["high_growth_pct", "value"]) == 25.0
    ok, _, _ = apply_site_edits(sites, edited_frame(sites, {(0, "electrical_capacity_mw"): 9.0}))
    edited = exports.scenario_frame(run_scenario(ok, ScenarioParams(), assumptions=replace(DEFAULT_ASSUMPTIONS, high_growth_pct=30.0))).set_index("parameter")
    assert edited.at["facility_data_source", "value"] == "edited in app" and float(edited.at["high_growth_pct", "value"]) == 30.0
