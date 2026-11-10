import io

import pandas as pd
import pytest

from models.capital import CostAssumptions, WEIGHTS, planned_projects, project_cost, select_within_budget
from models.scenarios import preset_params, run_scenario
from scripts.generate_data import generate


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_cost_calculation():
    c = CostAssumptions(power_per_mw_usd_m=10, cooling_per_mwe_usd_m=2, per_rack_usd_m=0.05)
    assert project_cost(2, 3, 100, c) == pytest.approx(20 + 6 + 5)
    assert project_cost(0, 0, 0, c) == 0


def test_configurable_costs_change_projects(sites):
    a = planned_projects(sites, CostAssumptions()).cost_usd_m.sum()
    b = planned_projects(sites, CostAssumptions(power_per_mw_usd_m=18)).cost_usd_m.sum()
    assert b > a
    r = run_scenario(sites, preset_params("Baseline"), CostAssumptions(power_per_mw_usd_m=18))
    assert r.projects.cost_usd_m.sum() == pytest.approx(b)


def test_csv_planned_cost_matches_default_costs(sites):
    pp = planned_projects(sites, CostAssumptions()).set_index("site_id")
    for r in sites.itertuples():
        assert pp.at[r.site_id, "cost_usd_m"] == pytest.approx(r.estimated_project_cost_usd_m, abs=0.01)


def test_prioritization_is_deterministic_and_urgency_ordered(sites):
    r1 = run_scenario(sites, preset_params("Baseline")).projects
    r2 = run_scenario(sites, preset_params("Baseline")).projects
    assert list(r1.site_id) == list(r2.site_id)
    assert r1.iloc[0].site_id == "DC3"
    assert r1.priority_score.between(0, 100).all()


def test_select_within_budget_skips_and_continues():
    df = pd.DataFrame({"site_id": ["A", "B", "C"], "cost_usd_m": [60.0, 50.0, 30.0]})
    out = select_within_budget(df, 100)
    assert list(out.funding_status) == ["Funded", "Unfunded", "Funded"]
    assert out.cumulative_funded_usd_m.iloc[-1] == 90


def test_dataset_reproducible(sites):
    regenerated = pd.read_csv(io.StringIO(generate().to_csv(index=False, float_format="%.2f")))
    pd.testing.assert_frame_equal(regenerated, sites, check_dtype=False)
    assert sites.electrical_capacity_mw.sum() == 45.0 and round(sites.electrical_demand_mw.sum(), 6) == 32.5
