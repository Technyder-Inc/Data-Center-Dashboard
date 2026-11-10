"""Risk classification, site and portfolio summaries, and rule-based recommendations."""
from __future__ import annotations

import pandas as pd

from models.capital import LEAD_TIME_MONTHS
from models.forecast import RESOURCE_META, RESOURCES, aggregate_exhaustion

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "info": 3}


def classify_risk(peak_pct: float, exhaustion_month, warn_pct: float, critical_pct: float) -> str:
    """Critical: demand exceeds capacity within the horizon. High: peak >= critical threshold.
    Medium: peak >= warning threshold. Low otherwise."""
    if exhaustion_month is not None and not pd.isna(exhaustion_month):
        return "Critical"
    if peak_pct >= critical_pct - 1e-9:
        return "High"
    if peak_pct >= warn_pct - 1e-9:
        return "Medium"
    return "Low"


def site_summary(ra: pd.DataFrame, fc: pd.DataFrame, sites: pd.DataFrame, params) -> pd.DataFrame:
    power_fc = fc[(fc["resource"] == "power")].set_index(["site_id", "month"])["demand"]
    rows = []
    for s in sites.itertuples():
        r = ra[ra["site_id"] == s.site_id].set_index("resource").loc[list(RESOURCES)]
        ex = r["first_exhaustion_month"].dropna()
        if len(ex):
            first_m = int(ex.min())
            tied = ex[ex == first_m].index
            limiting = max(tied, key=lambda x: (r.at[x, "peak_util_pct"], -RESOURCES.index(x)))
            basis = "exhaustion"
        else:
            first_m = None
            limiting = max(RESOURCES, key=lambda x: (r.at[x, "peak_util_pct"], -RESOURCES.index(x)))
            basis = "peak utilization"
        peak_res = max(RESOURCES, key=lambda x: (r.at[x, "peak_util_pct"], -RESOURCES.index(x)))
        peak = float(r.at[peak_res, "peak_util_pct"])
        warn = r["first_warning_month"].dropna()
        row = {
            "site_id": s.site_id,
            "site_name": s.site_name,
            "location": s.location,
            "risk_level": classify_risk(peak, first_m, params.warn_pct, params.critical_pct),
            "first_limiting_resource": limiting,
            "limiting_basis": basis,
            "earliest_exhaustion_month": first_m,
            "first_warning_month": int(warn.min()) if len(warn) else None,
            "peak_util_pct": peak,
            "peak_resource": peak_res,
            "peak_month": int(r.at[peak_res, "peak_month"]),
            "power_demand_month12_mw": float(power_fc.loc[(s.site_id, 12)]),
            "power_demand_month24_mw": float(power_fc.loc[(s.site_id, 24)]),
            "power_demand_month36_mw": float(power_fc.loc[(s.site_id, 36)]),
        }
        for res in RESOURCES:
            row[f"{res}_util_month0_pct"] = float(r.at[res, "month0_util_pct"])
            row[f"{res}_util_horizon_pct"] = float(r.at[res, "horizon_util_pct"])
            row[f"{res}_exhaustion_month"] = r.at[res, "first_exhaustion_month"]
        rows.append(row)
    df = pd.DataFrame(rows)
    df["earliest_exhaustion_month"] = df["earliest_exhaustion_month"].astype("Int64")
    df["first_warning_month"] = df["first_warning_month"].astype("Int64")
    return df


def portfolio_summary(ps: pd.DataFrame, ss: pd.DataFrame, sites: pd.DataFrame, params) -> dict:
    H = params.horizon

    def at(res, month, col):
        return float(ps[(ps["resource"] == res) & (ps["month"] == month)][col].iloc[0])

    out = {"horizon": H}
    for res, meta in RESOURCE_META.items():
        cap0 = float(sites[meta["cap"]].sum())
        dem0 = float(sites[meta["dem"]].sum())
        out[f"{res}_baseline_capacity"] = cap0
        out[f"{res}_baseline_demand"] = dem0
        out[f"{res}_baseline_util_pct"] = 100.0 * dem0 / cap0
        out[f"{res}_month0_capacity"] = at(res, 0, "capacity")
        out[f"{res}_month0_demand"] = at(res, 0, "demand")
        out[f"{res}_month0_util_pct"] = at(res, 0, "utilization_pct")
        out[f"{res}_month0_headroom"] = at(res, 0, "headroom")
        out[f"{res}_horizon_capacity"] = at(res, H, "capacity")
        out[f"{res}_horizon_demand"] = at(res, H, "demand")
        out[f"{res}_horizon_util_pct"] = at(res, H, "utilization_pct")
        out[f"{res}_horizon_headroom"] = at(res, H, "headroom")
        win = ps[(ps["resource"] == res) & (ps["month"] <= H)]
        out[f"{res}_peak_util_pct"] = float(win["utilization_pct"].max())
    for m in (12, 24, 36):
        out[f"power_demand_month{m}"] = at("power", m, "demand")

    out["sites_approaching"] = int((ss["peak_util_pct"] >= params.warn_pct - 1e-9).sum())
    out["sites_exhausted"] = int(ss["earliest_exhaustion_month"].notna().sum())
    out["site_count"] = len(ss)

    ex = ss.dropna(subset=["earliest_exhaustion_month"]).sort_values(
        ["earliest_exhaustion_month", "peak_util_pct"], ascending=[True, False]
    )
    if len(ex):
        top = ex.iloc[0]
        out["earliest_site"] = top["site_id"]
        out["earliest_resource"] = top["first_limiting_resource"]
        out["earliest_month"] = int(top["earliest_exhaustion_month"])
    else:
        out["earliest_site"] = out["earliest_resource"] = out["earliest_month"] = None

    agg = aggregate_exhaustion(ps, H)
    out["aggregate_exhaustion_by_resource"] = agg
    hits = {r: m for r, m in agg.items() if m is not None}
    if hits:
        r = min(hits, key=lambda k: (hits[k], RESOURCES.index(k)))
        out["aggregate_resource"], out["aggregate_month"] = r, hits[r]
    else:
        out["aggregate_resource"] = out["aggregate_month"] = None
    out["site_lead_months"] = (
        out["aggregate_month"] - out["earliest_month"]
        if out["aggregate_month"] is not None and out["earliest_month"] is not None
        else None
    )

    if out["aggregate_month"] is not None:
        level = "Critical"
    elif out["sites_exhausted"] > 0:
        level = "High"
    elif out["sites_approaching"] > 0:
        level = "Medium"
    else:
        level = "Low"
    out["portfolio_risk"] = level
    return out


def build_recommendations(sites, params, ss, pf, ranked, whatif, manual_cost, applied) -> list[dict]:
    """Deterministic rules. Every item cites a modeled site, resource, percentage, month or cost."""
    H = params.horizon
    recs: list[dict] = []

    def add(sev, title, detail, site=None, resource=None, month=None):
        recs.append({"severity": sev, "title": title, "detail": detail, "site_id": site, "resource": resource, "month": month})

    ss_sorted = ss.sort_values(["earliest_exhaustion_month", "peak_util_pct"], ascending=[True, False], na_position="last")
    for s in ss_sorted.itertuples():
        res = s.first_limiting_resource
        label, unit = RESOURCE_META[res]["label"], RESOURCE_META[res]["unit"]
        if not pd.isna(s.earliest_exhaustion_month):
            m = int(s.earliest_exhaustion_month)
            cap = float(sites.set_index("site_id").at[s.site_id, RESOURCE_META[res]["cap"]])
            if res == "cooling":
                add("critical" if m < 18 else "high", f"{s.site_id} approaching cooling limit",
                    f"Cooling demand exceeds capacity in month {m} (baseline cooling capacity {cap:.1f} {unit}, peak {s.peak_util_pct:.1f}%).",
                    s.site_id, res, m)
            elif res == "power":
                when = "before month 18" if m < 18 else f"in month {m}"
                add("critical" if m < 18 else "high", f"{s.site_id} needs electrical capacity {when}",
                    f"Power demand exceeds capacity in month {m} (baseline capacity {cap:.1f} {unit}, peak {s.peak_util_pct:.1f}%).",
                    s.site_id, res, m)
            else:
                add("critical" if m < 18 else "high", f"{s.site_id} rack capacity exhausted",
                    f"Occupied racks exceed {cap:.0f} racks in month {m} (peak {s.peak_util_pct:.1f}%).",
                    s.site_id, res, m)
        elif s.peak_util_pct >= params.warn_pct - 1e-9:
            add("medium", f"{s.site_id} {label.lower()} nearing threshold",
                f"{label} utilization peaks at {s.peak_util_pct:.1f}% in month {s.peak_month}, above the {params.warn_pct:g}% warning threshold.",
                s.site_id, s.peak_resource, int(s.peak_month))

    if pf["earliest_month"] is not None:
        res = pf["earliest_resource"]
        unit = RESOURCE_META[res]["unit"]
        spare = pf[f"{res}_horizon_headroom"]
        if pf["aggregate_month"] is None:
            add("high", "Site constraint precedes any portfolio constraint",
                f"{pf['earliest_site']} reaches its {res} limit in month {pf['earliest_month']}, while aggregate {res} stays at "
                f"{pf[f'{res}_horizon_util_pct']:.1f}% by month {H} with {spare:.1f} {unit} spare. Portfolio headroom cannot offset a single-site limit.",
                pf["earliest_site"], res, pf["earliest_month"])
        else:
            add("high", "Site constraint precedes portfolio exhaustion",
                f"{pf['earliest_site']} reaches its {res} limit in month {pf['earliest_month']}, "
                f"{pf['site_lead_months']} months before aggregate {pf['aggregate_resource']} is exhausted in month {pf['aggregate_month']}.",
                pf["earliest_site"], res, pf["earliest_month"])

    if len(ranked):
        needed = ranked[ranked["exhaustion_month_before"].notna()].sort_values("exhaustion_month_before")
        if len(needed):
            parts = [
                f"{r.site_id} by month {max(0, int(r.exhaustion_month_before) - LEAD_TIME_MONTHS)} (exhaustion month {int(r.exhaustion_month_before)})"
                for r in needed.itertuples()
            ]
            add("high", "Recommended expansion schedule",
                "Activate " + "; ".join(parts) + f". Assumes a {LEAD_TIME_MONTHS}-month commissioning lead time.")
        unfunded = ranked[ranked["funding_status"] == "Unfunded"]
        funded_cost = float(ranked.loc[ranked["funding_status"] == "Funded", "cost_usd_m"].sum())
        if len(unfunded) and params.fund_planned_projects:
            exposed = unfunded[unfunded["exhaustion_month_before"].notna()]
            tail = (
                f" Unfunded sites with modeled exhaustion: {', '.join(exposed['site_id'])}." if len(exposed) else ""
            )
            add("high" if len(exposed) else "medium", "Budget leaves projects unfunded",
                f"Budget ${params.budget_usd_m:.1f}M funds ${funded_cost:.1f}M; {len(unfunded)} project(s) unfunded "
                f"({', '.join(unfunded['site_id'])}) requiring ${unfunded['cost_usd_m'].sum():.1f}M.{tail}")

    if manual_cost > params.budget_usd_m + 1e-9:
        add("high", "Expansion request exceeds capital budget",
            f"Proposed expansion costs ${manual_cost:.1f}M against a ${params.budget_usd_m:.1f}M budget, a shortfall of ${manual_cost - params.budget_usd_m:.1f}M.")

    d = whatif.get("delay")
    if d:
        add("medium", "Impact of delaying investment",
            f"Delaying the {d['site_id']} expansion by {d['delay']} months (month {d['base_month']} to {d['base_month'] + d['delay']}) "
            f"changes months over capacity within the horizon from {d['over_before']} to {d['over_after']}.",
            d["site_id"], None, d["base_month"])
    e = whatif.get("efficiency")
    if e:
        after = "no exhaustion within the horizon" if e["after"] is None else f"month {e['after']}"
        add("medium", "Capacity optimization opportunity",
            f"A {e['pct']:g}% demand reduction would move {e['site_id']} {e['resource']} exhaustion from month {e['before']} to {after}.",
            e["site_id"], e["resource"], e["before"])

    if not recs:
        top = ss.sort_values("peak_util_pct", ascending=False).iloc[0]
        add("info", "No capacity constraint in horizon",
            f"No site exceeds the {params.warn_pct:g}% warning threshold through month {H}. Highest peak: {top['site_id']} "
            f"{top['peak_resource']} at {top['peak_util_pct']:.1f}% in month {top['peak_month']}.")

    recs.sort(key=lambda r: (SEVERITY_ORDER[r["severity"]], r["month"] if r["month"] is not None else 99))
    for i, r in enumerate(recs, 1):
        r["priority"] = i
    return recs
