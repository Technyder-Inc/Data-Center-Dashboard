"""Scenario presets and the single orchestration entry point used by every page."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from models import capital, risk
from models.forecast import (
    RESOURCE_META,
    Expansion,
    ScenarioParams,
    build_forecast,
    portfolio_series,
    resource_analysis,
)
from utils.validation import ValidationError, validate_params, validate_sites

PRESETS = ("Baseline", "High Growth", "Infrastructure Expansion", "Efficiency Optimization", "Budget-Constrained")
HIGH_GROWTH_PCT = 25.0
EFFICIENCY_PCT = 10.0
DEFAULT_BUDGET_USD_M = 100.0
DEFAULT_EXPANSION = {"site_id": "DC3", "power_mw": 4.0, "cooling_mwe": 4.0, "racks": 100.0, "month": 12}
WHATIF_EFFICIENCY_PCT = 10.0
WHATIF_DELAY_MONTHS = 6


def preset_params(name: str, horizon: int = 36, warn_pct: float = 85.0, critical_pct: float = 95.0,
                  budget_usd_m: float = DEFAULT_BUDGET_USD_M) -> ScenarioParams:
    if name not in PRESETS:
        raise ValueError(f"Unknown scenario: {name}")
    p = ScenarioParams(name=name, horizon=horizon, warn_pct=warn_pct, critical_pct=critical_pct, budget_usd_m=budget_usd_m)
    if name == "High Growth":
        p.growth_mode, p.growth_value_pct = "override", HIGH_GROWTH_PCT
    elif name == "Infrastructure Expansion":
        p.expansions = (Expansion(**DEFAULT_EXPANSION),)
    elif name == "Efficiency Optimization":
        p.efficiency_pct = EFFICIENCY_PCT
    elif name == "Budget-Constrained":
        p.fund_planned_projects = True
    return p


def baseline_like(params: ScenarioParams) -> ScenarioParams:
    """Original assumptions with the same horizon, thresholds and budget for before/after comparison."""
    return ScenarioParams(name="Baseline", horizon=params.horizon, warn_pct=params.warn_pct,
                          critical_pct=params.critical_pct, budget_usd_m=params.budget_usd_m)


@dataclass
class ScenarioResult:
    params: ScenarioParams
    costs: capital.CostAssumptions
    sites: pd.DataFrame
    forecast: pd.DataFrame
    analysis: pd.DataFrame
    site_summary: pd.DataFrame
    portfolio_series: pd.DataFrame
    portfolio: dict
    projects: pd.DataFrame
    applied_expansions: list
    manual_cost_usd_m: float
    funded_cost_usd_m: float
    recommendations: list
    warnings: list = field(default_factory=list)

    @property
    def total_investment_usd_m(self) -> float:
        return self.manual_cost_usd_m + self.funded_cost_usd_m


def _evaluate(sites, params, expansions):
    p = replace(params, expansions=tuple(expansions))
    fc = build_forecast(sites, p)
    ra = resource_analysis(fc, sites, p)
    return p, fc, ra, risk.site_summary(ra, fc, sites, p)


def _site_row(ss, site_id):
    return ss[ss["site_id"] == site_id].iloc[0]


def _months_over(fc, site_id, horizon):
    w = fc[(fc["site_id"] == site_id) & (fc["month"] <= horizon)]
    return int(w.groupby("month")["exhausted"].any().sum())


def _project_effects(sites, params, manual, ss0, ra0, ranked):
    rows = []
    for r in ranked.itertuples():
        e = Expansion(r.site_id, r.power_mw, r.cooling_mwe, r.racks, int(r.activation_month), "planned")
        _, _, ra1, ss1 = _evaluate(sites, params, list(manual) + [e])
        s1 = _site_row(ss1, r.site_id)
        res = r.limiting_resource
        before = ra0[(ra0["site_id"] == r.site_id) & (ra0["resource"] == res)].iloc[0]
        after = ra1[(ra1["site_id"] == r.site_id) & (ra1["resource"] == res)].iloc[0]
        rows.append(
            {
                "exhaustion_month_after": s1["earliest_exhaustion_month"],
                "peak_util_pct_after": float(s1["peak_util_pct"]),
                "risk_level_after": s1["risk_level"],
                "limiting_resource_headroom_before": float(before["horizon_headroom"]),
                "limiting_resource_headroom_after": float(after["horizon_headroom"]),
                "activation_after_exhaustion": bool(
                    not pd.isna(r.exhaustion_month_before) and int(r.activation_month) > int(r.exhaustion_month_before)
                ),
            }
        )
    out = pd.concat([ranked.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    for c in ("exhaustion_month_before", "exhaustion_month_after"):
        out[c] = out[c].astype("Int64")
    return out


def run_scenario(sites: pd.DataFrame, params: ScenarioParams, costs: capital.CostAssumptions | None = None) -> ScenarioResult:
    costs = costs or capital.CostAssumptions()
    site_rep = validate_sites(sites)
    site_rep.raise_if_invalid()
    validate_params(params, sites["site_id"].tolist()).raise_if_invalid()
    if min(costs.power_per_mw_usd_m, costs.cooling_per_mwe_usd_m, costs.per_rack_usd_m) < 0:
        raise ValidationError(["Unit costs must not be negative"])
    sites = sites.reset_index(drop=True)
    warnings = list(site_rep.warnings)

    manual = list(params.expansions)
    manual_cost = sum(capital.expansion_cost(e, costs) for e in manual)
    p0, fc0, ra0, ss0 = _evaluate(sites, params, manual)

    planned = capital.planned_projects(sites, costs)
    ranked = capital.prioritize(planned, ss0, params.horizon)
    available = max(params.budget_usd_m - manual_cost, 0.0)
    ranked = capital.select_within_budget(ranked, available)
    ranked = _project_effects(sites, params, manual, ss0, ra0, ranked) if len(ranked) else ranked

    funded = ranked[ranked["funding_status"] == "Funded"] if len(ranked) else ranked
    funded_cost = float(funded["cost_usd_m"].sum()) if len(funded) and params.fund_planned_projects else 0.0
    applied = manual + (capital.expansions_from_projects(funded) if params.fund_planned_projects and len(funded) else [])
    p, fc, ra, ss = _evaluate(sites, params, applied)
    ps = portfolio_series(fc)
    pf = risk.portfolio_summary(ps, ss, sites, p)

    whatif = _whatif(sites, params, applied, ss, pf)
    recs = risk.build_recommendations(sites, p, ss, pf, ranked, whatif, manual_cost, applied)

    if manual_cost > params.budget_usd_m + 1e-9:
        warnings.append(
            f"Proposed expansion cost ${manual_cost:.1f}M exceeds the ${params.budget_usd_m:.1f}M budget by "
            f"${manual_cost - params.budget_usd_m:.1f}M. The expansion is still modeled as requested; no results were adjusted."
        )
    if params.fund_planned_projects and len(ranked):
        unfunded = ranked[ranked["funding_status"] == "Unfunded"]
        if len(unfunded):
            warnings.append(
                f"Budget of ${available:.1f}M (after manual expansion) cannot fund {', '.join(unfunded['site_id'])}. "
                "These projects are excluded from the forecast."
            )
    for e in manual:
        row = _site_row(ss0, e.site_id)
        m = row["earliest_exhaustion_month"]
        if not pd.isna(m) and e.month > int(m):
            warnings.append(
                f"{e.site_id} expansion activates in month {e.month}, after modeled exhaustion in month {int(m)}. "
                "The site operates over capacity until activation."
            )
    if params.fund_planned_projects and len(ranked):
        for r in ranked[(ranked["funding_status"] == "Funded") & ranked["activation_after_exhaustion"]].itertuples():
            warnings.append(
                f"Funded {r.site_id} project activates in month {r.activation_month}, after modeled {r.limiting_resource} "
                f"exhaustion in month {int(r.exhaustion_month_before)}. Capacity arrives late."
            )
    touched = {e.site_id for e in applied}
    for s in ss.itertuples():
        if not pd.isna(s.earliest_exhaustion_month) and (s.site_id in touched or params.efficiency_pct > 0):
            warnings.append(
                f"{s.site_id} still exhausts {s.first_limiting_resource} in month {int(s.earliest_exhaustion_month)} under this scenario."
            )

    return ScenarioResult(p, costs, sites, fc, ra, ss, ps, pf, ranked, applied, manual_cost, funded_cost, recs, warnings)


def _whatif(sites, params, applied, ss, pf) -> dict:
    out: dict = {}
    site = pf["earliest_site"]
    if site is None:
        return out
    res = pf["earliest_resource"]
    if params.efficiency_pct < WHATIF_EFFICIENCY_PCT:
        _, _, _, ss_e = _evaluate(sites, replace(params, efficiency_pct=WHATIF_EFFICIENCY_PCT), applied)
        after = _site_row(ss_e, site)["earliest_exhaustion_month"]
        out["efficiency"] = {"site_id": site, "resource": res, "pct": WHATIF_EFFICIENCY_PCT,
                             "before": pf["earliest_month"], "after": None if pd.isna(after) else int(after)}
    mine = [e for e in applied if e.site_id == site]
    if mine:
        base = mine[0]
        delayed = [replace(e, month=min(e.month + WHATIF_DELAY_MONTHS, 36)) if e is base else e for e in applied]
        _, fc_b, _, _ = _evaluate(sites, params, applied)
        _, fc_d, _, _ = _evaluate(sites, params, delayed)
        out["delay"] = {"site_id": site, "delay": WHATIF_DELAY_MONTHS, "base_month": base.month,
                        "over_before": _months_over(fc_b, site, params.horizon),
                        "over_after": _months_over(fc_d, site, params.horizon)}
    return out


def scenario_insights(base: ScenarioResult, scn: ScenarioResult) -> list[str]:
    """Deterministic before/after statements for the active scenario."""
    b, s, H = base.portfolio, scn.portfolio, scn.params.horizon
    out = []
    if b["earliest_month"] is None and s["earliest_month"] is None:
        out.append(f"No site exhausts any resource within {H} months in either the baseline or this scenario.")
    elif b["earliest_month"] is None:
        out.append(f"Baseline has no exhaustion within {H} months; this scenario introduces a limit at {s['earliest_site']} {s['earliest_resource']} in month {s['earliest_month']}.")
    elif s["earliest_month"] is None:
        out.append(f"The earliest constraint ({b['earliest_site']} {b['earliest_resource']}, month {b['earliest_month']} in the baseline) is removed within {H} months.")
    else:
        d = s["earliest_month"] - b["earliest_month"]
        out.append(
            f"Earliest constraint moves from {b['earliest_site']} {b['earliest_resource']} month {b['earliest_month']} "
            f"to {s['earliest_site']} {s['earliest_resource']} month {s['earliest_month']} ({d:+d} months)."
        )
    for res, meta in RESOURCE_META.items():
        gain = s[f"{res}_horizon_capacity"] - b[f"{res}_horizon_capacity"]
        if abs(gain) > 1e-9:
            out.append(f"{meta['label']} capacity at month {H} rises by {gain:,.1f} {meta['unit']} through activated expansions.")
    dd = s["power_horizon_demand"] - b["power_horizon_demand"]
    if abs(dd) > 1e-9:
        out.append(f"Power demand at month {H} is {s['power_horizon_demand']:.1f} MW versus {b['power_horizon_demand']:.1f} MW in the baseline ({dd:+.1f} MW).")
    out.append(f"Sites at or above the warning threshold: {s['sites_approaching']} (baseline {b['sites_approaching']}); sites exhausted: {s['sites_exhausted']} (baseline {b['sites_exhausted']}).")
    if scn.total_investment_usd_m:
        out.append(f"Capital committed: ${scn.total_investment_usd_m:.1f}M of ${scn.params.budget_usd_m:.1f}M budget; remaining ${scn.params.budget_usd_m - scn.total_investment_usd_m:.1f}M.")
    return out


OUTCOME = {
    "Critical": ("Portfolio Shortfall", "red"),
    "High": ("Site Constraint", "red"),
    "Medium": ("Reduce Risk", "amber"),
    "Low": ("Maintain Headroom", "green"),
}


def compare_presets(sites: pd.DataFrame, params: ScenarioParams, costs: capital.CostAssumptions) -> pd.DataFrame:
    """All five presets evaluated at the active horizon, thresholds and budget."""
    rows = []
    for name in PRESETS:
        pp = preset_params(name, params.horizon, params.warn_pct, params.critical_pct, params.budget_usd_m)
        r = run_scenario(sites, pp, costs)
        pf = r.portfolio
        rows.append(
            {
                "scenario": name,
                "capacity_added_mw": pf["power_horizon_capacity"] - pf["power_baseline_capacity"],
                "demand_mw": pf["power_horizon_demand"],
                "utilization_pct": pf["power_horizon_util_pct"],
                "headroom_mw": pf["power_horizon_headroom"],
                "earliest_month": pf["earliest_month"],
                "aggregate_month": pf["aggregate_month"],
                "cost_usd_m": r.total_investment_usd_m,
                "risk": pf["portfolio_risk"],
                "outcome": OUTCOME[pf["portfolio_risk"]][0],
            }
        )
    return pd.DataFrame(rows)


def risk_indicators(r: ScenarioResult) -> list[tuple[str, str, str]]:
    """(indicator, level, evidence) from modeled results."""
    p = r.params
    out = []
    for res, meta in RESOURCE_META.items():
        a = r.analysis[r.analysis["resource"] == res]
        ex = a["first_exhaustion_month"].dropna()
        peak = a.sort_values("peak_util_pct", ascending=False).iloc[0]
        level = risk.classify_risk(float(peak["peak_util_pct"]), int(ex.min()) if len(ex) else None, p.warn_pct, p.critical_pct)
        ev = f"{peak['site_id']} peak {peak['peak_util_pct']:.0f}%" + (f", first limit month {int(ex.min())}" if len(ex) else "")
        out.append((f"{meta['label']} capacity", level, ev))
    late = [e for e in r.applied_expansions if not r.site_summary[r.site_summary["site_id"] == e.site_id].empty
            and not pd.isna(_site_row(r.site_summary, e.site_id)["earliest_exhaustion_month"])
            and e.month > int(_site_row(r.site_summary, e.site_id)["earliest_exhaustion_month"])]
    out.append(("Expansion schedule", "High" if late else "Low" if r.applied_expansions else "Medium",
                f"{len(late)} expansion(s) activate after exhaustion" if late else (f"{len(r.applied_expansions)} expansion(s) on time" if r.applied_expansions else "No expansion applied")))
    used = r.total_investment_usd_m
    ratio = used / p.budget_usd_m if p.budget_usd_m else (1.0 if used else 0.0)
    out.append(("Capital budget", "High" if ratio > 1 else "Medium" if ratio > 0.8 else "Low", f"${used:.1f}M of ${p.budget_usd_m:.1f}M committed"))
    return out
