"""Input validation for the site dataset and scenario parameters.

Invalid inputs (impossible physical values) raise ValidationError. Legitimate
modeled overload (demand above capacity) is allowed and reported as a warning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

import numpy as np
import pandas as pd

MAX_MONTH = 36
HORIZONS = (6, 12, 18, 24, 30, 36)

SITE_COLUMNS = [
    "site_id",
    "site_name",
    "location",
    "electrical_capacity_mw",
    "electrical_demand_mw",
    "cooling_capacity_mwe",
    "cooling_demand_mwe",
    "rack_capacity",
    "occupied_racks",
    "annual_growth_pct",
    "planned_power_expansion_mw",
    "planned_cooling_expansion_mwe",
    "planned_additional_racks",
    "expansion_activation_month",
    "estimated_project_cost_usd_m",
]
NUMERIC_COLUMNS = SITE_COLUMNS[3:]
POSITIVE_COLUMNS = ["electrical_capacity_mw", "cooling_capacity_mwe", "rack_capacity"]
INTEGER_COLUMNS = ["rack_capacity", "occupied_racks", "planned_additional_racks", "expansion_activation_month"]
GROWTH_RANGE = (-50.0, 100.0)

# One table of numeric bounds, used by every input widget, the facility grid and the server-side checks.
LIMITS = {
    "portfolio_growth_pct": (0.0, 60.0),
    "growth_pct": GROWTH_RANGE,
    "growth_adjust_pts": (-10.0, 25.0),
    "efficiency_pct": (0.0, 60.0),
    "expansion_power_mw": (0.0, 100.0),
    "expansion_cooling_mwe": (0.0, 100.0),
    "expansion_racks": (0, 5000),
    "month": (0, MAX_MONTH),
    "budget_usd_m": (0.0, 1000.0),
    "warn_pct": (50, 99),
    "critical_pct": (51, 100),
    "cost_per_mw": (0.0, 100.0),
    "cost_per_mwe": (0.0, 100.0),
    "cost_per_rack": (0.0, 5.0),
    "capacity_mw": (0.0, 500.0),
    "demand_mw": (0.0, 1000.0),
    "rack_capacity": (0, 50000),
    "occupied_racks": (0, 100000),
    "project_cost_usd_m": (0.0, 100000.0),
}
SITE_COLUMN_LIMITS = {
    "electrical_capacity_mw": "capacity_mw", "cooling_capacity_mwe": "capacity_mw",
    "electrical_demand_mw": "demand_mw", "cooling_demand_mwe": "demand_mw",
    "rack_capacity": "rack_capacity", "occupied_racks": "occupied_racks",
    "annual_growth_pct": "growth_pct",
    "planned_power_expansion_mw": "expansion_power_mw", "planned_cooling_expansion_mwe": "expansion_cooling_mwe",
    "planned_additional_racks": "expansion_racks", "expansion_activation_month": "month",
    "estimated_project_cost_usd_m": "project_cost_usd_m",
}


def bounds(name: str) -> tuple:
    return LIMITS[name]


def _within(value, name: str) -> bool:
    lo, hi = LIMITS[name]
    return lo <= value <= hi


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_invalid(self) -> None:
        if self.errors:
            raise ValidationError(self.errors)


def validate_sites(df: pd.DataFrame) -> ValidationReport:
    rep = ValidationReport()
    missing = [c for c in SITE_COLUMNS if c not in df.columns]
    if missing:
        rep.errors.append(f"Missing required columns: {', '.join(missing)}")
        return rep
    if df.empty:
        rep.errors.append("Dataset contains no sites")
        return rep
    if df["site_id"].duplicated().any():
        rep.errors.append("Duplicate site_id values")
    if df[SITE_COLUMNS].isna().any().any():
        rep.errors.append("Dataset contains missing values")
        return rep
    num = df[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    if num.isna().any().any():
        rep.errors.append("Non-numeric values in numeric columns")
        return rep
    if not np.isfinite(num.to_numpy()).all():
        rep.errors.append("All dataset numbers must be finite")
        return rep
    if any(not pd.api.types.is_numeric_dtype(df[c]) for c in NUMERIC_COLUMNS):
        rep.errors.append("Numeric columns must have numeric dtypes")
        return rep

    for col in NUMERIC_COLUMNS:
        if col == "annual_growth_pct":
            continue
        bad = df.loc[num[col] < 0, "site_id"].tolist()
        if bad:
            rep.errors.append(f"{col} must not be negative (sites: {', '.join(bad)})")
    for col in POSITIVE_COLUMNS:
        bad = df.loc[num[col] <= 0, "site_id"].tolist()
        if bad:
            rep.errors.append(f"{col} must be greater than zero (sites: {', '.join(bad)})")
    for col, limit in SITE_COLUMN_LIMITS.items():
        lo, hi = LIMITS[limit]
        bad = df.loc[(num[col] < lo) | (num[col] > hi), "site_id"].tolist()
        if bad:
            rep.errors.append(f"{col} must be within {lo:g} to {hi:g} (sites: {', '.join(bad)})")
    for col in INTEGER_COLUMNS:
        bad = df.loc[(num[col] % 1) != 0, "site_id"].tolist()
        if bad:
            rep.errors.append(f"{col} must be a whole number (sites: {', '.join(bad)})")
    if rep.errors:
        return rep

    for _, r in df.iterrows():
        if r["occupied_racks"] > r["rack_capacity"]:
            rep.warnings.append(
                f"{r['site_id']}: occupied racks ({r['occupied_racks']:.0f}) exceed rack capacity "
                f"({r['rack_capacity']:.0f}). Modeled as baseline overcapacity."
            )
        if r["electrical_demand_mw"] > r["electrical_capacity_mw"]:
            rep.warnings.append(f"{r['site_id']}: baseline electrical demand exceeds capacity. Modeled as overload.")
        if r["cooling_demand_mwe"] > r["cooling_capacity_mwe"]:
            rep.warnings.append(f"{r['site_id']}: baseline cooling demand exceeds capacity. Modeled as overload.")
    return rep


def validate_params(params, site_ids: list[str]) -> ValidationReport:
    rep = ValidationReport()
    values = [params.growth_value_pct, params.efficiency_pct, params.budget_usd_m,
              params.warn_pct, params.critical_pct, *params.site_growth_overrides.values()]
    values.extend(v for e in params.expansions for v in (e.power_mw, e.cooling_mwe, e.racks, e.month))
    if not all(isinstance(v, (int, float, np.number)) and isfinite(v) for v in values):
        rep.errors.append("Scenario numbers must be finite numeric values")
        return rep
    if params.horizon not in HORIZONS:
        rep.errors.append(f"Horizon must be one of {', '.join(map(str, HORIZONS))} months")
    if params.growth_mode not in ("site", "adjust", "override"):
        rep.errors.append("growth_mode must be 'site', 'adjust' or 'override'")
    if params.growth_mode == "override" and not _within(params.growth_value_pct, "portfolio_growth_pct"):
        rep.errors.append("Portfolio growth must be within %g to %g percent" % LIMITS["portfolio_growth_pct"])
    if params.growth_mode == "adjust" and not _within(params.growth_value_pct, "growth_adjust_pts"):
        rep.errors.append("Portfolio growth adjustment must be within %g to %g points" % LIMITS["growth_adjust_pts"])
    for sid, val in params.site_growth_overrides.items():
        if sid not in site_ids:
            rep.errors.append(f"Growth override for unknown site {sid}")
        elif not _within(val, "growth_pct"):
            rep.errors.append(f"{sid} growth override must be within %g to %g percent" % LIMITS["growth_pct"])
    if not _within(params.efficiency_pct, "efficiency_pct"):
        rep.errors.append("Efficiency improvement must be within %g to %g percent" % LIMITS["efficiency_pct"])
    if not _within(params.budget_usd_m, "budget_usd_m"):
        rep.errors.append("Budget must be within %g to %g USD millions" % LIMITS["budget_usd_m"])
    if not (_within(params.warn_pct, "warn_pct") and _within(params.critical_pct, "critical_pct") and params.warn_pct < params.critical_pct):
        rep.errors.append("Thresholds must satisfy warning %g to %g, critical %g to %g, and warning below critical" % (*LIMITS["warn_pct"], *LIMITS["critical_pct"]))
    for e in params.expansions:
        if e.site_id not in site_ids:
            rep.errors.append(f"Expansion references unknown site {e.site_id}")
        for value, name, label in ((e.power_mw, "expansion_power_mw", "power"), (e.cooling_mwe, "expansion_cooling_mwe", "cooling"),
                                   (e.racks, "expansion_racks", "racks")):
            if not _within(value, name):
                rep.errors.append(f"Expansion {label} for {e.site_id} must be within %g to %g" % LIMITS[name])
        if not _within(e.month, "month") or e.month % 1:
            rep.errors.append(f"Expansion activation month for {e.site_id} must be a whole number from 0 to {MAX_MONTH}")
        if e.racks % 1:
            rep.errors.append(f"Expansion racks for {e.site_id} must be a whole number")
    return rep


def validate_costs(costs) -> list[str]:
    """Unit costs (USD millions) must be finite and within bounds."""
    errors = []
    for value, name, label in ((costs.power_per_mw_usd_m, "cost_per_mw", "power cost per MW"),
                               (costs.cooling_per_mwe_usd_m, "cost_per_mwe", "cooling cost per MWe"),
                               (costs.per_rack_usd_m, "cost_per_rack", "cost per rack")):
        if not isinstance(value, (int, float, np.number)) or not isfinite(value) or not _within(value, name):
            errors.append(f"{label[0].upper() + label[1:]} must be within %g to %g USD millions" % LIMITS[name])
    return errors
