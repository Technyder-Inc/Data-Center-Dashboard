"""Session state: one set of keys drives every page. Widgets use these keys directly."""
from pathlib import Path

import pandas as pd
import streamlit as st

from models.capital import CostAssumptions
from models.forecast import Expansion, ScenarioParams
from models.scenarios import compare_presets, run_scenario, DEFAULT_BUDGET_USD_M, DEFAULT_EXPANSION, EFFICIENCY_PCT, HIGH_GROWTH_PCT

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_sites.csv"
GROWTH_MODES = {"site": "Site rates (dataset)", "adjust": "Adjust all sites (+/- points)", "override": "Override all sites (%)"}
MODE_BY_LABEL = {v: k for k, v in GROWTH_MODES.items()}

SCENARIO_KEYS = {
    "growth_mode": GROWTH_MODES["site"],
    "growth_adjust": 0.0,
    "growth_override": 15.0,
    "override_sites": [],
    "exp_site": DEFAULT_EXPANSION["site_id"],
    "exp_power": 0.0,
    "exp_cooling": 0.0,
    "exp_racks": 0,
    "exp_month": DEFAULT_EXPANSION["month"],
    "efficiency": 0,
    "budget": DEFAULT_BUDGET_USD_M,
    "fund_projects": False,
}
VIEW_KEYS = {"horizon": 36, "warn_pct": 85, "crit_pct": 95}
COST_DEFAULTS = {"cost_power": 9.0, "cost_cooling": 3.5, "cost_rack": 0.02}


@st.cache_data
def load_sites() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def _site_growth_defaults(sites: pd.DataFrame) -> dict:
    return {f"sg_{r.site_id}": float(r.annual_growth_pct) for r in sites.itertuples()}


def init_state(sites: pd.DataFrame) -> None:
    defaults = {"scenario_name": "Baseline", **SCENARIO_KEYS, **VIEW_KEYS, **COST_DEFAULTS, **_site_growth_defaults(sites)}
    for k, v in defaults.items():
        st.session_state.setdefault(k, list(v) if isinstance(v, list) else v)


def persist() -> None:
    """Widget state is dropped when a widget is not rendered on the current page; re-assign to keep it."""
    for k in list(st.session_state.keys()):
        if k in ("scenario_name",) or k in SCENARIO_KEYS or k in VIEW_KEYS or k in COST_DEFAULTS or k.startswith(("sg_", "ui_")):
            st.session_state[k] = st.session_state[k]


def mark_custom() -> None:
    st.session_state["scenario_name"] = "Custom"


def _reset_assumptions(sites: pd.DataFrame) -> None:
    for k, v in SCENARIO_KEYS.items():
        st.session_state[k] = list(v) if isinstance(v, list) else v
    for k, v in _site_growth_defaults(sites).items():
        st.session_state[k] = v


def apply_preset(name: str) -> None:
    """Reset every scenario assumption, then apply the preset. Horizon, thresholds and unit costs are kept."""
    sites = load_sites()
    _reset_assumptions(sites)
    ss = st.session_state
    if name == "High Growth":
        ss["growth_mode"] = GROWTH_MODES["override"]
        ss["growth_override"] = HIGH_GROWTH_PCT
    elif name == "Infrastructure Expansion":
        ss["exp_site"] = DEFAULT_EXPANSION["site_id"]
        ss["exp_power"] = DEFAULT_EXPANSION["power_mw"]
        ss["exp_cooling"] = DEFAULT_EXPANSION["cooling_mwe"]
        ss["exp_racks"] = int(DEFAULT_EXPANSION["racks"])
        ss["exp_month"] = DEFAULT_EXPANSION["month"]
    elif name == "Efficiency Optimization":
        ss["efficiency"] = int(EFFICIENCY_PCT)
    elif name == "Budget-Constrained":
        ss["fund_projects"] = True
    ss["scenario_name"] = name


def reset_to_baseline() -> None:
    sites = load_sites()
    apply_preset("Baseline")
    for k, v in {**VIEW_KEYS, **COST_DEFAULTS}.items():
        st.session_state[k] = v
    _reset_assumptions(sites)


def sync_thresholds(changed: str) -> None:
    ss = st.session_state
    if ss["crit_pct"] <= ss["warn_pct"]:
        if changed == "warn_pct":
            ss["crit_pct"] = min(100, ss["warn_pct"] + 1)
        else:
            ss["warn_pct"] = max(50, ss["crit_pct"] - 1)


def costs_from_state() -> CostAssumptions:
    s = st.session_state
    return CostAssumptions(float(s["cost_power"]), float(s["cost_cooling"]), float(s["cost_rack"]))


def params_from_state() -> ScenarioParams:
    s = st.session_state
    mode = MODE_BY_LABEL[s["growth_mode"]]
    value = {"site": 0.0, "adjust": s["growth_adjust"], "override": s["growth_override"]}[mode]
    expansions = ()
    if s["exp_power"] > 0 or s["exp_cooling"] > 0 or s["exp_racks"] > 0:
        expansions = (Expansion(s["exp_site"], float(s["exp_power"]), float(s["exp_cooling"]), float(s["exp_racks"]), int(s["exp_month"])),)
    return ScenarioParams(
        name=s["scenario_name"],
        horizon=int(s["horizon"]),
        growth_mode=mode,
        growth_value_pct=float(value),
        site_growth_overrides={sid: float(s[f"sg_{sid}"]) for sid in s["override_sites"]},
        efficiency_pct=float(s["efficiency"]),
        expansions=expansions,
        budget_usd_m=float(s["budget"]),
        fund_planned_projects=bool(s["fund_projects"]),
        warn_pct=float(s["warn_pct"]),
        critical_pct=float(s["crit_pct"]),
    )



def get_results():
    return st.session_state["_result"], st.session_state["_baseline"]


EXP_CHOICES = {"None (Baseline)": 0.0, "Add 1 MW (Site 3)": 1.0, "Add 2 MW (Site 3)": 2.0, "Add 4 MW (Site 3)": 4.0}
EXP_CUSTOM = "Custom (see Scenario Planning)"


def expansion_label() -> str:
    s = st.session_state
    if s["exp_cooling"] == 0 and s["exp_racks"] == 0 and (s["exp_power"] == 0 or (s["exp_site"] == "DC3" and s["exp_month"] == 0)):
        for label, mw in EXP_CHOICES.items():
            if s["exp_power"] == mw:
                return label
    return EXP_CUSTOM


def set_growth() -> None:
    st.session_state["growth_mode"] = GROWTH_MODES["override"]
    mark_custom()


def set_expansion() -> None:
    s = st.session_state
    choice = s["ui_exp_choice"]
    if choice == EXP_CUSTOM:
        return
    s["exp_site"], s["exp_power"], s["exp_cooling"], s["exp_racks"], s["exp_month"] = "DC3", EXP_CHOICES[choice], 0.0, 0, 0
    mark_custom()


def apply_quick_expansion() -> None:
    apply_preset("Infrastructure Expansion")
    s = st.session_state
    s["exp_site"], s["exp_power"], s["exp_cooling"], s["exp_racks"], s["exp_month"] = "DC3", 1.0, 0.0, 0, 0


@st.cache_data(show_spinner=False)
def run_main(params: ScenarioParams, costs: CostAssumptions):
    return run_scenario(load_sites(), params, costs)


@st.cache_data(show_spinner=False)
def _compare_cached(horizon: int, warn_pct: float, critical_pct: float, budget: float, costs: CostAssumptions):
    base = ScenarioParams(horizon=horizon, warn_pct=warn_pct, critical_pct=critical_pct, budget_usd_m=budget)
    return compare_presets(load_sites(), base, costs)


def get_compare():
    """Preset comparison. Depends only on horizon, thresholds, budget and unit costs, so growth changes reuse it."""
    p = params_from_state()
    return _compare_cached(p.horizon, p.warn_pct, p.critical_pct, p.budget_usd_m, costs_from_state())
