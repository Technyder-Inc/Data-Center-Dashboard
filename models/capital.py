"""Illustrative capital costing and deterministic investment prioritization."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from models.forecast import Expansion

LEAD_TIME_MONTHS = 6
RISK_SCORE = {"Low": 0.0, "Medium": 40.0, "High": 70.0, "Critical": 100.0}
WEIGHTS = {"timing": 0.35, "peak_utilization": 0.25, "risk_level": 0.15, "resource_fit": 0.15, "cost": 0.10}
RESOURCE_FIELD = {"power": "power_mw", "cooling": "cooling_mwe", "racks": "racks"}


@dataclass(frozen=True)
class CostAssumptions:
    """Illustrative unit costs in USD millions. Not engineering cost claims."""

    power_per_mw_usd_m: float = 9.0
    cooling_per_mwe_usd_m: float = 3.5
    per_rack_usd_m: float = 0.02


def project_cost(power_mw: float, cooling_mwe: float, racks: float, costs: CostAssumptions) -> float:
    return power_mw * costs.power_per_mw_usd_m + cooling_mwe * costs.cooling_per_mwe_usd_m + racks * costs.per_rack_usd_m


def expansion_cost(e: Expansion, costs: CostAssumptions) -> float:
    return project_cost(e.power_mw, e.cooling_mwe, e.racks, costs)


def planned_projects(sites: pd.DataFrame, costs: CostAssumptions) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "site_id": sites["site_id"],
            "power_mw": sites["planned_power_expansion_mw"].astype(float),
            "cooling_mwe": sites["planned_cooling_expansion_mwe"].astype(float),
            "racks": sites["planned_additional_racks"].astype(float),
            "activation_month": sites["expansion_activation_month"].astype(int),
        }
    )
    df = df[(df["power_mw"] > 0) | (df["cooling_mwe"] > 0) | (df["racks"] > 0)].reset_index(drop=True)
    df["cost_usd_m"] = [project_cost(r.power_mw, r.cooling_mwe, r.racks, costs) for r in df.itertuples()]
    return df


def prioritize(projects: pd.DataFrame, site_summary: pd.DataFrame, horizon: int, weights: dict | None = None,
               risk_scores: dict | None = None) -> pd.DataFrame:
    """Score each project 0-100 using documented weights, rank descending (ties by site_id)."""
    if projects.empty:
        return projects.assign(priority_score=[], priority_rank=[])
    weights = weights or WEIGHTS
    risk_scores = risk_scores or RISK_SCORE
    ss = site_summary.set_index("site_id")
    max_cost = max(projects["cost_usd_m"].max(), 1e-9)
    rows = []
    for p in projects.itertuples():
        s = ss.loc[p.site_id]
        m = s["earliest_exhaustion_month"]
        timing = 0.0 if pd.isna(m) else 100.0 * (1.0 - float(m) / horizon)
        peak = min(max((float(s["peak_util_pct"]) - 50.0) / 50.0, 0.0), 1.0) * 100.0
        risk = risk_scores[s["risk_level"]]
        fit = 100.0 if getattr(p, RESOURCE_FIELD[s["first_limiting_resource"]]) > 0 else 0.0
        cost = 100.0 * (1.0 - p.cost_usd_m / max_cost)
        score = (
            weights["timing"] * timing
            + weights["peak_utilization"] * peak
            + weights["risk_level"] * risk
            + weights["resource_fit"] * fit
            + weights["cost"] * cost
        )
        rows.append(
            {
                "timing_score": timing,
                "peak_util_score": peak,
                "risk_score": risk,
                "resource_fit_score": fit,
                "cost_score": cost,
                "priority_score": score,
                "limiting_resource": s["first_limiting_resource"],
                "exhaustion_month_before": m,
                "peak_util_pct_before": float(s["peak_util_pct"]),
                "risk_level": s["risk_level"],
            }
        )
    out = pd.concat([projects.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    out = out.sort_values(["priority_score", "site_id"], ascending=[False, True]).reset_index(drop=True)
    out["priority_rank"] = range(1, len(out) + 1)
    return out


def select_within_budget(ranked: pd.DataFrame, budget_usd_m: float) -> pd.DataFrame:
    """Greedy in rank order: fund a project if it fits the remaining budget, otherwise leave it unfunded and continue."""
    out = ranked.copy()
    remaining = max(budget_usd_m, 0.0)
    status, cumulative = [], []
    spent = 0.0
    for r in out.itertuples():
        if r.cost_usd_m <= remaining + 1e-9:
            remaining -= r.cost_usd_m
            spent += r.cost_usd_m
            status.append("Funded")
        else:
            status.append("Unfunded")
        cumulative.append(spent)
    out["funding_status"] = status
    out["cumulative_funded_usd_m"] = cumulative
    return out


def expansions_from_projects(df: pd.DataFrame) -> list[Expansion]:
    return [
        Expansion(r.site_id, r.power_mw, r.cooling_mwe, r.racks, int(r.activation_month), "planned")
        for r in df.itertuples()
    ]
