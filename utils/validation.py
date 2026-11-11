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
    lo, hi = GROWTH_RANGE
    bad = df.loc[(num["annual_growth_pct"] < lo) | (num["annual_growth_pct"] > hi), "site_id"].tolist()
    if bad:
        rep.errors.append(f"annual_growth_pct must be within {lo:g} to {hi:g} (sites: {', '.join(bad)})")
    for col in INTEGER_COLUMNS:
        bad = df.loc[(num[col] % 1) != 0, "site_id"].tolist()
        if bad:
            rep.errors.append(f"{col} must be a whole number (sites: {', '.join(bad)})")
    bad = df.loc[num["expansion_activation_month"] > MAX_MONTH, "site_id"].tolist()
    if bad:
        rep.errors.append(f"expansion_activation_month must be 0 to {MAX_MONTH} (sites: {', '.join(bad)})")
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
    lo, hi = GROWTH_RANGE
    if params.growth_mode == "override" and not lo <= params.growth_value_pct <= hi:
        rep.errors.append(f"Portfolio growth must be within {lo:g} to {hi:g} percent")
    for sid, val in params.site_growth_overrides.items():
        if sid not in site_ids:
            rep.errors.append(f"Growth override for unknown site {sid}")
        elif not lo <= val <= hi:
            rep.errors.append(f"{sid} growth override must be within {lo:g} to {hi:g} percent")
    if not 0 <= params.efficiency_pct < 100:
        rep.errors.append("Efficiency improvement must be at least 0 and below 100 percent")
    if params.budget_usd_m < 0:
        rep.errors.append("Budget must not be negative")
    if not 0 < params.warn_pct < params.critical_pct <= 100:
        rep.errors.append("Thresholds must satisfy 0 < warning < critical <= 100")
    for e in params.expansions:
        if e.site_id not in site_ids:
            rep.errors.append(f"Expansion references unknown site {e.site_id}")
        if min(e.power_mw, e.cooling_mwe, e.racks) < 0:
            rep.errors.append(f"Expansion for {e.site_id} contains negative capacity")
        if not 0 <= e.month <= MAX_MONTH or e.month % 1:
            rep.errors.append(f"Expansion activation month for {e.site_id} must be 0 to {MAX_MONTH}")
        if e.racks % 1:
            rep.errors.append(f"Expansion racks for {e.site_id} must be a whole number")
    return rep
