"""Centralized monthly forecasting engine (months 0 to 36).

Power, cooling and rack demand are modeled independently:

    demand(m) = baseline_demand * (1 - efficiency) * (1 + growth) ** (m / 12)

Expansion capacity becomes available in its activation month, not before.
Exhaustion is the first month where demand strictly exceeds capacity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from utils.validation import MAX_MONTH, validate_params, validate_sites

EPS = 1e-9
RESOURCES = ("power", "cooling", "racks")
RESOURCE_META = {
    "power": {"label": "Power", "unit": "MW", "cap": "electrical_capacity_mw", "dem": "electrical_demand_mw", "exp": "power_mw"},
    "cooling": {"label": "Cooling", "unit": "MWe", "cap": "cooling_capacity_mwe", "dem": "cooling_demand_mwe", "exp": "cooling_mwe"},
    "racks": {"label": "Racks", "unit": "racks", "cap": "rack_capacity", "dem": "occupied_racks", "exp": "racks"},
}


@dataclass(frozen=True)
class Expansion:
    site_id: str
    power_mw: float = 0.0
    cooling_mwe: float = 0.0
    racks: float = 0.0
    month: int = 0
    source: str = "manual"


@dataclass
class ScenarioParams:
    name: str = "Baseline"
    horizon: int = 36
    growth_mode: str = "site"  # site | adjust | override
    growth_value_pct: float = 0.0
    site_growth_overrides: dict = field(default_factory=dict)
    efficiency_pct: float = 0.0
    expansions: tuple = ()
    budget_usd_m: float = 100.0
    fund_planned_projects: bool = False
    warn_pct: float = 85.0
    critical_pct: float = 95.0


def effective_growth_pct(sites: pd.DataFrame, params: ScenarioParams) -> pd.Series:
    """Site override > portfolio override/adjustment > dataset site rate."""
    g = sites.set_index("site_id")["annual_growth_pct"].astype(float)
    if params.growth_mode == "override":
        g = pd.Series(float(params.growth_value_pct), index=g.index)
    elif params.growth_mode == "adjust":
        g = g + params.growth_value_pct
    for sid, val in params.site_growth_overrides.items():
        g[sid] = float(val)
    return g


def build_forecast(sites: pd.DataFrame, params: ScenarioParams) -> pd.DataFrame:
    validate_sites(sites).raise_if_invalid()
    validate_params(params, sites["site_id"].tolist()).raise_if_invalid()
    ids = sites["site_id"].tolist()
    idx = {s: i for i, s in enumerate(ids)}
    months = np.arange(0, MAX_MONTH + 1)
    growth = effective_growth_pct(sites, params).reindex(ids).to_numpy() / 100.0
    factor = (1.0 + growth)[:, None] ** (months / 12.0)[None, :] * (1.0 - params.efficiency_pct / 100.0)

    frames = []
    for res, meta in RESOURCE_META.items():
        demand = sites[meta["dem"]].to_numpy(float)[:, None] * factor
        base_cap = sites[meta["cap"]].to_numpy(float)
        added = np.zeros_like(demand)
        for e in params.expansions:
            added[idx[e.site_id], months >= e.month] += getattr(e, meta["exp"])
        capacity = base_cap[:, None] + added
        frames.append(
            pd.DataFrame(
                {
                    "month": np.tile(months, len(ids)),
                    "site_id": np.repeat(ids, len(months)),
                    "resource": res,
                    "demand": demand.ravel(),
                    "capacity": capacity.ravel(),
                    "capacity_added": added.ravel(),
                }
            )
        )
    fc = pd.concat(frames, ignore_index=True)
    fc["utilization_pct"] = 100.0 * fc["demand"] / fc["capacity"]
    fc["headroom"] = fc["capacity"] - fc["demand"]
    fc["exhausted"] = fc["demand"] > fc["capacity"] * (1 + EPS)
    return fc


def _first(months: np.ndarray, mask: np.ndarray):
    hit = np.flatnonzero(mask)
    return int(months[hit[0]]) if hit.size else None


def resource_analysis(fc: pd.DataFrame, sites: pd.DataFrame, params: ScenarioParams) -> pd.DataFrame:
    """One row per site and resource, evaluated over months 0..horizon."""
    base = sites.set_index("site_id")
    win = fc[fc["month"] <= params.horizon]
    rows = []
    for (sid, res), g in win.groupby(["site_id", "resource"], sort=False):
        g = g.sort_values("month")
        m = g["month"].to_numpy()
        u = g["utilization_pct"].to_numpy()
        meta = RESOURCE_META[res]
        peak_i = int(np.argmax(u))
        rows.append(
            {
                "site_id": sid,
                "resource": res,
                "unit": meta["unit"],
                "baseline_demand": float(base.at[sid, meta["dem"]]),
                "baseline_capacity": float(base.at[sid, meta["cap"]]),
                "month0_demand": float(g["demand"].iloc[0]),
                "month0_capacity": float(g["capacity"].iloc[0]),
                "month0_util_pct": float(u[0]),
                "horizon_demand": float(g["demand"].iloc[-1]),
                "horizon_capacity": float(g["capacity"].iloc[-1]),
                "horizon_util_pct": float(u[-1]),
                "horizon_headroom": float(g["headroom"].iloc[-1]),
                "peak_util_pct": float(u[peak_i]),
                "peak_month": int(m[peak_i]),
                "first_warning_month": _first(m, u >= params.warn_pct - EPS),
                "first_critical_month": _first(m, u >= params.critical_pct - EPS),
                "first_exhaustion_month": _first(m, g["exhausted"].to_numpy()),
            }
        )
    df = pd.DataFrame(rows)
    for c in ("first_warning_month", "first_critical_month", "first_exhaustion_month"):
        df[c] = df[c].astype("Int64")
    return df


def portfolio_series(fc: pd.DataFrame) -> pd.DataFrame:
    """Weighted portfolio utilization: sum of demand over sum of capacity."""
    g = fc.groupby(["month", "resource"], as_index=False)[["demand", "capacity"]].sum()
    g["utilization_pct"] = 100.0 * g["demand"] / g["capacity"]
    g["headroom"] = g["capacity"] - g["demand"]
    g["exhausted"] = g["demand"] > g["capacity"] * (1 + EPS)
    return g


def aggregate_exhaustion(ps: pd.DataFrame, horizon: int) -> dict:
    """First month in the horizon where aggregate portfolio demand exceeds aggregate capacity."""
    out = {}
    for res in RESOURCES:
        g = ps[(ps["resource"] == res) & (ps["month"] <= horizon)].sort_values("month")
        out[res] = _first(g["month"].to_numpy(), g["exhausted"].to_numpy())
    return out
