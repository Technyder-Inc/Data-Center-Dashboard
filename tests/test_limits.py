import math
from dataclasses import replace

import pytest

from models.assumptions import DEFAULT_ASSUMPTIONS, validate_assumptions
from models.capital import CostAssumptions
from models.forecast import Expansion, ScenarioParams
from models.scenarios import run_scenario
from utils.validation import LIMITS, SITE_COLUMN_LIMITS, ValidationError, validate_costs, validate_params, validate_sites

IDS = ["DC1", "DC2", "DC3", "DC4", "DC5", "DC6"]


def outside(name):
    lo, hi = LIMITS[name]
    step = 1 if isinstance(hi, int) else 0.5
    return lo - step, hi + step


def params_with(name, value):
    return {
        "portfolio_growth_pct": ScenarioParams(growth_mode="override", growth_value_pct=value),
        "growth_adjust_pts": ScenarioParams(growth_mode="adjust", growth_value_pct=value),
        "growth_pct": ScenarioParams(site_growth_overrides={"DC1": value}),
        "efficiency_pct": ScenarioParams(efficiency_pct=value),
        "budget_usd_m": ScenarioParams(budget_usd_m=value),
        "warn_pct": ScenarioParams(warn_pct=value, critical_pct=100),
        "critical_pct": ScenarioParams(warn_pct=50, critical_pct=value),
        "expansion_power_mw": ScenarioParams(expansions=(Expansion("DC1", power_mw=value),)),
        "expansion_cooling_mwe": ScenarioParams(expansions=(Expansion("DC1", cooling_mwe=value),)),
        "expansion_racks": ScenarioParams(expansions=(Expansion("DC1", racks=value),)),
        "month": ScenarioParams(expansions=(Expansion("DC1", power_mw=1, month=value),)),
    }[name]


SCENARIO_LIMITS = ["portfolio_growth_pct", "growth_adjust_pts", "growth_pct", "efficiency_pct", "budget_usd_m", "warn_pct",
                   "critical_pct", "expansion_power_mw", "expansion_cooling_mwe", "expansion_racks", "month"]


@pytest.mark.parametrize("name", SCENARIO_LIMITS)
def test_scenario_inputs_reject_outside_and_accept_the_boundaries(name):
    lo, hi = LIMITS[name]
    below, above = outside(name)
    for value in (lo, hi):
        assert validate_params(params_with(name, value), IDS).ok, (name, value)
    for value in (below, above):
        assert not validate_params(params_with(name, value), IDS).ok, (name, value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), None, "12"])
def test_scenario_inputs_reject_non_numbers(bad):
    for p in (ScenarioParams(budget_usd_m=bad), ScenarioParams(efficiency_pct=bad), ScenarioParams(growth_mode="override", growth_value_pct=bad),
              ScenarioParams(expansions=(Expansion("DC1", power_mw=bad),))):
        assert not validate_params(p, IDS).ok


def test_whole_number_fields_reject_fractions():
    assert not validate_params(ScenarioParams(expansions=(Expansion("DC1", racks=10.5),)), IDS).ok
    assert not validate_params(ScenarioParams(expansions=(Expansion("DC1", power_mw=1, month=3.5),)), IDS).ok


def test_threshold_order_is_enforced():
    assert not validate_params(ScenarioParams(warn_pct=90, critical_pct=90), IDS).ok
    assert not validate_params(ScenarioParams(warn_pct=95, critical_pct=90), IDS).ok


def with_value(sites, column, value, is_int):
    df = sites.copy()
    df[column] = df[column].astype(int if is_int else float)
    df.loc[0, column] = value
    return df


@pytest.mark.parametrize("column", sorted(SITE_COLUMN_LIMITS))
def test_dataset_columns_reject_outside_and_accept_the_boundaries(sites, column):
    lo, hi = LIMITS[SITE_COLUMN_LIMITS[column]]
    is_int = isinstance(hi, int)
    must_be_positive = column in ("electrical_capacity_mw", "cooling_capacity_mwe", "rack_capacity")
    for v in (lo, hi):
        if must_be_positive and v == 0:
            assert not validate_sites(with_value(sites, column, v, is_int)).ok
        else:
            assert validate_sites(with_value(sites, column, v, is_int)).ok, (column, v)
    for v in (hi + (1 if is_int else 0.5), lo - (1 if is_int else 0.5)):
        assert not validate_sites(with_value(sites, column, v, is_int)).ok, (column, v)


def test_unit_costs_are_bounded():
    assert validate_costs(CostAssumptions()) == []
    for name, field in (("cost_per_mw", "power_per_mw_usd_m"), ("cost_per_mwe", "cooling_per_mwe_usd_m"), ("cost_per_rack", "per_rack_usd_m")):
        lo, hi = LIMITS[name]
        for bad in (lo - 0.01, hi + 0.01, math.nan, math.inf):
            assert validate_costs(replace(CostAssumptions(), **{field: bad})), (name, bad)
        for good in (lo, hi):
            assert validate_costs(replace(CostAssumptions(), **{field: good})) == []


def test_engine_refuses_bad_costs_and_params(sites):
    with pytest.raises(ValidationError):
        run_scenario(sites, ScenarioParams(), CostAssumptions(power_per_mw_usd_m=1e9))
    with pytest.raises(ValidationError):
        run_scenario(sites, ScenarioParams(budget_usd_m=1e9))


def test_assumption_editor_bounds():
    for field, name in (("expansion_power_mw", "expansion_power_mw"), ("expansion_cooling_mwe", "expansion_cooling_mwe"),
                        ("expansion_racks", "expansion_racks")):
        for bad in outside(name):
            assert validate_assumptions(replace(DEFAULT_ASSUMPTIONS, **{field: bad}), IDS)
    for bad in (-1, 61):
        assert validate_assumptions(replace(DEFAULT_ASSUMPTIONS, high_growth_pct=bad), IDS)
        assert validate_assumptions(replace(DEFAULT_ASSUMPTIONS, efficiency_pct=bad), IDS)
    assert validate_assumptions(replace(DEFAULT_ASSUMPTIONS, expansion_month=2.5), IDS)
