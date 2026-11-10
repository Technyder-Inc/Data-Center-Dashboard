"""Deterministic generator for data/synthetic_sites.csv.

Baseline operating figures come from the original prototype (DC-A..DC-F renamed DC1..DC6).
Planned expansions use a seeded RNG so reruns reproduce the file byte for byte.

    python scripts/generate_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.capital import CostAssumptions, project_cost  # noqa: E402
from models.scenarios import preset_params, run_scenario  # noqa: E402

SEED = 20240601
OUT = ROOT / "data" / "synthetic_sites.csv"

# site_id, name, location, power cap, power demand, cooling cap, cooling demand, rack cap, occupied, growth %
BASELINE = [
    ("DC1", "Northern Virginia", "Ashburn, VA", 8.0, 5.9, 7.5, 5.6, 420, 315, 13),
    ("DC2", "Central Ohio", "Columbus, OH", 6.0, 3.9, 5.8, 4.1, 310, 193, 11),
    ("DC3", "Dallas", "Dallas, TX", 10.0, 8.0, 9.2, 7.8, 510, 416, 18),
    ("DC4", "Phoenix", "Phoenix, AZ", 7.0, 5.5, 6.4, 5.1, 365, 277, 16),
    ("DC5", "Atlanta", "Atlanta, GA", 9.0, 6.2, 8.7, 6.5, 460, 309, 14),
    ("DC6", "Denver", "Denver, CO", 5.0, 3.0, 4.8, 3.2, 265, 158, 12),
]
COLUMNS = [
    "site_id", "site_name", "location", "electrical_capacity_mw", "electrical_demand_mw",
    "cooling_capacity_mwe", "cooling_demand_mwe", "rack_capacity", "occupied_racks", "annual_growth_pct",
]


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    df = pd.DataFrame(BASELINE, columns=COLUMNS)
    power = np.round(df["electrical_capacity_mw"] * rng.uniform(0.25, 0.50, len(df)) * 2) / 2
    cooling = np.round(df["cooling_capacity_mwe"] * rng.uniform(0.25, 0.50, len(df)) * 2) / 2
    racks = np.round(df["rack_capacity"] * rng.uniform(0.25, 0.50, len(df)) / 10) * 10
    df["planned_power_expansion_mw"] = power
    df["planned_cooling_expansion_mwe"] = cooling
    df["planned_additional_racks"] = racks.astype(int)
    df["expansion_activation_month"] = rng.integers(8, 22, len(df))
    costs = CostAssumptions()
    df["estimated_project_cost_usd_m"] = [
        round(project_cost(r.planned_power_expansion_mw, r.planned_cooling_expansion_mwe, r.planned_additional_racks, costs), 2)
        for r in df.itertuples()
    ]
    res = run_scenario(df.assign(risk_status=""), preset_params("Baseline", horizon=24))
    df["risk_status"] = res.site_summary["risk_level"].to_numpy()
    return df


def main() -> None:
    df = generate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, float_format="%.2f", lineterminator="\n")
    print(f"Wrote {OUT} ({len(df)} sites)")


if __name__ == "__main__":
    main()
