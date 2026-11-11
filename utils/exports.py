"""CSV exports. Every frame is derived from the active ScenarioResult so downloads match the dashboard."""
from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import pandas as pd

from models.capital import expansion_cost
from models.forecast import RESOURCE_META, effective_growth_pct


def _slug(result) -> str:
    return re.sub(r"[^a-z0-9]+", "_", result.params.name.lower()).strip("_")


def filename(result, kind: str) -> str:
    return f"capacity_{kind}_{_slug(result)}_{result.params.horizon}m.csv"


def facility_frame(result) -> pd.DataFrame:
    p = result.params
    ss = result.site_summary.set_index("site_id")
    growth = effective_growth_pct(result.sites, p)
    rows = []
    for s in result.sites.itertuples():
        r = ss.loc[s.site_id]
        row = {
            "scenario": p.name,
            "site_id": s.site_id,
            "site_name": s.site_name,
            "location": s.location,
            "effective_growth_pct": growth[s.site_id],
        }
        for res, meta in RESOURCE_META.items():
            a = result.analysis[(result.analysis["site_id"] == s.site_id) & (result.analysis["resource"] == res)].iloc[0]
            u = meta["unit"]
            row[f"{res}_baseline_capacity_{u}"] = a["baseline_capacity"]
            row[f"{res}_baseline_demand_{u}"] = a["baseline_demand"]
            row[f"{res}_month0_demand_{u}"] = a["month0_demand"]
            row[f"{res}_month0_capacity_{u}"] = a["month0_capacity"]
            row[f"{res}_month0_headroom_{u}"] = a["month0_capacity"] - a["month0_demand"]
            row[f"{res}_horizon_demand_{u}"] = a["horizon_demand"]
            row[f"{res}_horizon_capacity_{u}"] = a["horizon_capacity"]
            row[f"{res}_horizon_headroom_{u}"] = a["horizon_headroom"]
            row[f"{res}_horizon_utilization_pct"] = a["horizon_util_pct"]
            row[f"{res}_peak_utilization_pct"] = a["peak_util_pct"]
            row[f"{res}_first_exhaustion_month"] = a["first_exhaustion_month"]
        row.update(
            {
                "horizon_months": p.horizon,
                "first_limiting_resource": r["first_limiting_resource"],
                "earliest_exhaustion_month": r["earliest_exhaustion_month"],
                "risk_level": r["risk_level"],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def forecast_frame(result) -> pd.DataFrame:
    fc = result.forecast.copy()
    fc["unit"] = fc["resource"].map(lambda r: RESOURCE_META[r]["unit"])
    fc.insert(0, "scenario", result.params.name)
    return fc.rename(
        columns={
            "demand": "demand_units",
            "capacity": "capacity_units",
            "capacity_added": "capacity_added_units",
            "headroom": "headroom_units",
            "utilization_pct": "utilization_pct",
        }
    )[
        ["scenario", "month", "site_id", "resource", "unit", "demand_units", "capacity_units",
         "capacity_added_units", "headroom_units", "utilization_pct", "exhausted"]
    ]


DATASET = Path(__file__).resolve().parents[1] / "data" / "synthetic_sites.csv"


def _data_source(sites: pd.DataFrame) -> str:
    try:
        cols = [c for c in sites.columns if c not in ("risk_status", "estimated_project_cost_usd_m")]
        pd.testing.assert_frame_equal(pd.read_csv(DATASET)[cols], sites[cols].reset_index(drop=True), check_dtype=False)
        return "data/synthetic_sites.csv"
    except AssertionError:
        return "edited in app"


def scenario_frame(result) -> pd.DataFrame:
    p, pf = result.params, result.portfolio
    rows: list[tuple] = []

    def add(section, name, value, unit=""):
        rows.append((result.params.name, section, name, "" if value is None else value, unit))

    add("assumption", "facility_data_source", _data_source(result.sites))
    for f in fields(result.assumptions):
        add("model_assumption", f.name, getattr(result.assumptions, f.name))
    add("assumption", "forecast_horizon", p.horizon, "months")
    add("assumption", "growth_mode", p.growth_mode)
    add("assumption", "portfolio_growth_value", p.growth_value_pct, "percent")
    for sid, v in p.site_growth_overrides.items():
        add("assumption", f"site_growth_override_{sid}", v, "percent")
    add("assumption", "efficiency_demand_reduction", p.efficiency_pct, "percent")
    add("assumption", "warning_threshold", p.warn_pct, "percent")
    add("assumption", "critical_threshold", p.critical_pct, "percent")
    add("assumption", "capital_budget", p.budget_usd_m, "USD millions")
    add("assumption", "fund_planned_projects_within_budget", p.fund_planned_projects)
    add("assumption", "cost_power_per_mw", result.costs.power_per_mw_usd_m, "USD millions per MW")
    add("assumption", "cost_cooling_per_mwe", result.costs.cooling_per_mwe_usd_m, "USD millions per MWe")
    add("assumption", "cost_per_rack", result.costs.per_rack_usd_m, "USD millions per rack")
    for e in result.applied_expansions:
        add("expansion", f"{e.site_id}_{e.source}", f"power {e.power_mw:g} MW; cooling {e.cooling_mwe:g} MWe; racks {e.racks:g}; month {e.month}")
    for res, meta in RESOURCE_META.items():
        u = meta["unit"]
        add("result", f"{res}_baseline_capacity", pf[f"{res}_baseline_capacity"], u)
        add("result", f"{res}_baseline_demand", pf[f"{res}_baseline_demand"], u)
        add("result", f"{res}_month0_demand", pf[f"{res}_month0_demand"], u)
        add("result", f"{res}_horizon_capacity", pf[f"{res}_horizon_capacity"], u)
        add("result", f"{res}_horizon_demand", pf[f"{res}_horizon_demand"], u)
        add("result", f"{res}_horizon_utilization", pf[f"{res}_horizon_util_pct"], "percent")
        add("result", f"{res}_horizon_headroom", pf[f"{res}_horizon_headroom"], u)
        add("result", f"{res}_aggregate_exhaustion_month", pf["aggregate_exhaustion_by_resource"][res], "month")
    for m in (12, 24, 36):
        add("result", f"power_demand_month_{m}", pf[f"power_demand_month{m}"], "MW")
    add("result", "earliest_constraint_site", pf["earliest_site"])
    add("result", "earliest_constraint_resource", pf["earliest_resource"])
    add("result", "earliest_constraint_month", pf["earliest_month"], "month")
    add("result", "portfolio_aggregate_exhaustion_month", pf["aggregate_month"], "month")
    add("result", "sites_approaching_limits", pf["sites_approaching"], "sites")
    add("result", "sites_exhausted_within_horizon", pf["sites_exhausted"], "sites")
    add("result", "portfolio_risk", pf["portfolio_risk"])
    add("result", "manual_expansion_cost", result.manual_cost_usd_m, "USD millions")
    add("result", "funded_project_cost", result.funded_cost_usd_m, "USD millions")
    add("result", "total_investment", result.total_investment_usd_m, "USD millions")
    add("result", "remaining_budget", p.budget_usd_m - result.total_investment_usd_m, "USD millions")
    return pd.DataFrame(rows, columns=["scenario", "section", "parameter", "value", "unit"])


def capital_frame(result) -> pd.DataFrame:
    p = result.params
    rows = []
    for e in result.applied_expansions:
        if e.source != "manual":
            continue
        rows.append(
            {
                "scenario": p.name, "project_type": "manual expansion", "site_id": e.site_id, "priority_rank": None,
                "power_mw_added": e.power_mw, "cooling_mwe_added": e.cooling_mwe, "racks_added": e.racks,
                "activation_month": e.month, "cost_usd_m": expansion_cost(e, result.costs), "funding_status": "Proposed",
            }
        )
    for r in result.projects.itertuples():
        applied = p.fund_planned_projects and r.funding_status == "Funded"
        rows.append(
            {
                "scenario": p.name, "project_type": "planned project", "site_id": r.site_id, "priority_rank": r.priority_rank,
                "priority_score": round(r.priority_score, 2), "limiting_resource": r.limiting_resource,
                "power_mw_added": r.power_mw, "cooling_mwe_added": r.cooling_mwe, "racks_added": r.racks,
                "activation_month": r.activation_month, "cost_usd_m": r.cost_usd_m,
                "funding_status": r.funding_status + (" (applied)" if applied else " (not applied to forecast)" if r.funding_status == "Funded" else ""),
                "exhaustion_month_before": r.exhaustion_month_before, "exhaustion_month_after": r.exhaustion_month_after,
                "limiting_resource_headroom_before": r.limiting_resource_headroom_before,
                "limiting_resource_headroom_after": r.limiting_resource_headroom_after,
                "limiting_resource_headroom_unit": RESOURCE_META[r.limiting_resource]["unit"],
                "effect_basis": "candidate project added to active manual expansions; hypothetical even when unfunded",
                "budget_usd_m": p.budget_usd_m,
            }
        )
    return pd.DataFrame(rows, columns=["scenario", "project_type", "site_id", "priority_rank",
        "priority_score", "limiting_resource", "power_mw_added", "cooling_mwe_added", "racks_added",
        "activation_month", "cost_usd_m", "funding_status", "exhaustion_month_before", "exhaustion_month_after",
        "limiting_resource_headroom_before", "limiting_resource_headroom_after", "limiting_resource_headroom_unit",
        "effect_basis", "budget_usd_m"])


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
