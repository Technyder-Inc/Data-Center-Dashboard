"""Apply user edits to the facility dataset, with the same validation as the loaded file."""
from __future__ import annotations

import pandas as pd

from models.capital import CostAssumptions, project_cost
from models.scenarios import preset_params, run_scenario
from utils.validation import ValidationError, validate_sites

EDITABLE_COLUMNS = [
    "site_name", "location", "electrical_capacity_mw", "electrical_demand_mw", "cooling_capacity_mwe", "cooling_demand_mwe",
    "rack_capacity", "occupied_racks", "annual_growth_pct", "planned_power_expansion_mw", "planned_cooling_expansion_mwe",
    "planned_additional_racks", "expansion_activation_month",
]
INTEGER_COLUMNS = ["rack_capacity", "occupied_racks", "planned_additional_racks", "expansion_activation_month"]


def apply_site_edits(original: pd.DataFrame, edited: pd.DataFrame) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """Return (new dataset or None, errors, warnings). site_id is fixed; project cost and risk status are recomputed."""
    if list(edited["site_id"]) != list(original["site_id"]):
        return None, ["Facility IDs cannot be changed, added or removed"], []
    df = original.copy()
    for col in EDITABLE_COLUMNS:
        df[col] = edited[col].to_numpy() if col not in ("site_name", "location") else edited[col].astype(str).to_numpy()
    for col in df.columns:
        if col in EDITABLE_COLUMNS and col not in ("site_name", "location"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    report = validate_sites(df)
    if not report.ok:
        return None, report.errors, []
    for col in INTEGER_COLUMNS:
        df[col] = df[col].astype(int)
    costs = CostAssumptions()
    df["estimated_project_cost_usd_m"] = [
        round(project_cost(r.planned_power_expansion_mw, r.planned_cooling_expansion_mwe, r.planned_additional_racks, costs), 2)
        for r in df.itertuples()
    ]
    try:
        df["risk_status"] = run_scenario(df, preset_params("Baseline", horizon=24)).site_summary["risk_level"].to_numpy()
    except ValidationError as exc:
        return None, exc.errors, []
    return df, [], report.warnings


def matches_dataset(df: pd.DataFrame, dataset: pd.DataFrame) -> bool:
    """True when the editable columns are identical to the dataset, so nothing counts as edited."""
    try:
        pd.testing.assert_frame_equal(df[EDITABLE_COLUMNS].reset_index(drop=True), dataset[EDITABLE_COLUMNS].reset_index(drop=True), check_dtype=False)
        return True
    except AssertionError:
        return False
