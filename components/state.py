"""Session state: one set of keys drives every page. Widgets use these keys directly."""
from math import isfinite
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from models.capital import CostAssumptions
from models.forecast import Expansion, ScenarioParams
from models.assumptions import DEFAULT_ASSUMPTIONS, Assumptions
from models.scenarios import DEFAULT_BUDGET_USD_M, run_scenario
from utils.validation import LIMITS

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "synthetic_sites.csv"
GROWTH_MODES = {"site": "Site rates (dataset)", "adjust": "Adjust all sites (+/- points)", "override": "Override all sites (%)"}
MODE_BY_LABEL = {v: k for k, v in GROWTH_MODES.items()}

SCENARIO_KEYS = {
    "growth_mode": GROWTH_MODES["site"],
    "growth_adjust": 0.0,
    "growth_override": 15.0,
    "override_sites": [],
    "expansions": [],
    "exp_site": DEFAULT_ASSUMPTIONS.expansion_site,
    "exp_power": 0.0,
    "exp_cooling": 0.0,
    "exp_racks": 0,
    "exp_month": DEFAULT_ASSUMPTIONS.expansion_month,
    "efficiency": 0.0,
    "budget": DEFAULT_BUDGET_USD_M,
    "fund_projects": False,
}
VIEW_KEYS = {"horizon": 36, "warn_pct": 85, "crit_pct": 95}
COST_DEFAULTS = {"cost_power": 9.0, "cost_cooling": 3.5, "cost_rack": 0.02}


@st.cache_data
def load_sites() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def get_sites() -> pd.DataFrame:
    """Facility data in use: the in-app edited copy if there is one, otherwise the dataset file."""
    return st.session_state.get("sites_override", load_sites())


def get_assumptions() -> Assumptions:
    return st.session_state.get("assumptions", DEFAULT_ASSUMPTIONS)


def sites_edited() -> bool:
    return "sites_override" in st.session_state


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
    sites = get_sites()
    _reset_assumptions(sites)
    ss = st.session_state
    a = get_assumptions()
    if name == "High Growth":
        ss["growth_mode"] = GROWTH_MODES["override"]
        ss["growth_override"] = a.high_growth_pct
    elif name == "Infrastructure Expansion":
        ss["expansions"] = [_exp_dict(a.expansion_site, a.expansion_power_mw, a.expansion_cooling_mwe, a.expansion_racks, a.expansion_month)]
    elif name == "Efficiency Optimization":
        ss["efficiency"] = float(a.efficiency_pct)
    elif name == "Budget-Constrained":
        ss["fund_projects"] = True
    ss["scenario_name"] = name


def reset_to_baseline() -> None:
    sites = get_sites()
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
    expansions = tuple(Expansion(e["site"], float(e["power"]), float(e["cooling"]), float(e["racks"]), int(e["month"])) for e in s["expansions"])
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


EXP_NONE = "None (Baseline)"
# label -> (state key, unit, default amount, step)
EXP_RESOURCES = {
    "Add Power (MW)": ("exp_power", "MW", 1.0, 0.5),
    "Add Cooling (MWe)": ("exp_cooling", "MWe", 1.0, 0.5),
    "Add Racks": ("exp_racks", "racks", 50, 10),
}


def _exp_dict(site, power, cooling, racks, month) -> dict:
    return {"site": site, "power": float(power), "cooling": float(cooling), "racks": int(racks), "month": int(month)}


def exp_summary_label() -> str:
    n = len(st.session_state["expansions"])
    return EXP_NONE if n == 0 else f"{n} expansion{'s' if n > 1 else ''} planned"


def describe_expansion(e: dict) -> str:
    parts = [f"+{e['power']:g} MW" if e["power"] else "", f"+{e['cooling']:g} MWe" if e["cooling"] else "", f"+{e['racks']:g} racks" if e["racks"] else ""]
    return f"{e['site']}: {', '.join(p for p in parts if p)} from month {e['month']}"


def add_expansion(site, power=0.0, cooling=0.0, racks=0, month=0) -> None:
    if power <= 0 and cooling <= 0 and racks <= 0:
        return
    ss = st.session_state
    new = _exp_dict(site, power, cooling, racks, month)
    merged = False
    items = []
    for e in ss["expansions"]:
        if not merged and e["site"] == new["site"] and e["month"] == new["month"]:
            e = _exp_dict(e["site"], e["power"] + new["power"], e["cooling"] + new["cooling"], e["racks"] + new["racks"], e["month"])
            merged = True
        items.append(e)
    ss["expansions"] = items if merged else [*items, new]
    mark_custom()


def add_expansion_from_page() -> None:
    s = st.session_state
    add_expansion(s["exp_site"], s["exp_power"], s["exp_cooling"], s["exp_racks"], s["exp_month"])
    s["exp_power"], s["exp_cooling"], s["exp_racks"] = 0.0, 0.0, 0


def add_expansion_from_sidebar() -> None:
    s = st.session_state
    label = s["ui_exp_choice"]
    if label not in EXP_RESOURCES:
        return
    key = EXP_RESOURCES[label][0]
    amount = s[f"sb_amt_{key}"]
    add_expansion(s["sb_exp_site"], amount if key == "exp_power" else 0.0, amount if key == "exp_cooling" else 0.0,
                  amount if key == "exp_racks" else 0, s["sb_exp_month"])
    s["ui_exp_choice"] = exp_summary_label()


def remove_expansion(index: int) -> None:
    ss = st.session_state
    ss["expansions"] = [e for i, e in enumerate(ss["expansions"]) if i != index]
    ss["ui_exp_choice"] = exp_summary_label()
    mark_custom()


def clear_expansions() -> None:
    st.session_state["expansions"] = []
    st.session_state["ui_exp_choice"] = EXP_NONE
    mark_custom()


def set_growth() -> None:
    st.session_state["growth_mode"] = GROWTH_MODES["override"]
    mark_custom()


def expansion_impact(result, baseline) -> str | None:
    """Calculated summary of what the planned expansions changed."""
    exps = result.params.expansions
    if not exps:
        return None
    pf, bf, H = result.portfolio, baseline.portfolio, result.params.horizon
    gains = []
    for res, unit in (("power", "MW"), ("cooling", "MWe"), ("racks", "racks")):
        diff = pf[f"{res}_horizon_capacity"] - bf[f"{res}_horizon_capacity"]
        if abs(diff) > 1e-9:
            gains.append(f"{diff:+g} {unit}")
    sites = ", ".join(sorted({e.site_id for e in exps}))
    lead = f"Capacity at month {H}: {', '.join(gains) or 'none (activates after the horizon)'} from {len(exps)} expansion{'s' if len(exps) > 1 else ''} ({sites})."
    before, after = bf["earliest_month"], pf["earliest_month"]
    if before == after:
        if before is None:
            return f"{lead} No exhaustion within {H} months."
        site, res = pf["earliest_site"], pf["earliest_resource"]
        tail = f"First exhaustion stays month {before} ({site} {res})."
        touching = [e for e in exps if e.site_id == site]
        added = {r for e in touching for r, f in (("power", e.power_mw), ("cooling", e.cooling_mwe), ("racks", e.racks)) if f > 0}
        if not touching:
            tail += f" No expansion targets {site}, the first site to run out."
        elif res not in added:
            tail += f" {site}'s first limit is {res}, so these do not move it."
        return f"{lead} {tail}"
    now = f"month {after} ({pf['earliest_site']} {pf['earliest_resource']})" if after is not None else f"none within {H} months"
    return f"{lead} First exhaustion moves from month {before if before is not None else 'none'} to {now}."


@st.cache_data(show_spinner=False)
def run_main(params: ScenarioParams, costs: CostAssumptions, sites: pd.DataFrame, assumptions: Assumptions):
    return run_scenario(sites, params, costs, assumptions)


def reset_site_growth_defaults(sites: pd.DataFrame) -> None:
    """After facility data changes, point the per-site growth inputs at the new rates (overrides keep their own values)."""
    for sid, rate in ((r.site_id, float(r.annual_growth_pct)) for r in sites.itertuples()):
        if sid not in st.session_state["override_sites"]:
            st.session_state[f"sg_{sid}"] = rate


# stored widget values -> the limit that applies to them
KEY_LIMITS = {
    "growth_override": "portfolio_growth_pct", "growth_adjust": "growth_adjust_pts", "efficiency": "efficiency_pct", "budget": "budget_usd_m",
    "warn_pct": "warn_pct", "crit_pct": "critical_pct", "exp_power": "expansion_power_mw", "exp_cooling": "expansion_cooling_mwe",
    "exp_racks": "expansion_racks", "exp_month": "month", "cost_power": "cost_per_mw", "cost_cooling": "cost_per_mwe", "cost_rack": "cost_per_rack",
    "sb_amt_exp_power": "expansion_power_mw", "sb_amt_exp_cooling": "expansion_cooling_mwe", "sb_amt_exp_racks": "expansion_racks",
    "sb_exp_month": "month",
}
INTEGER_KEYS = {"exp_racks", "exp_month", "warn_pct", "crit_pct", "sb_exp_month", "sb_amt_exp_racks"}
WIDGET_DEFAULTS = {"sb_exp_month": 0, "sb_amt_exp_power": 1.0, "sb_amt_exp_cooling": 1.0, "sb_amt_exp_racks": 50}


def _valid_number(value, name: str, integer: bool = False) -> bool:
    lo, hi = LIMITS[name]
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)) or not isfinite(value):
        return False
    return lo <= value <= hi and (not integer or float(value).is_integer())


def _valid_expansion(e, site_ids) -> bool:
    try:
        return (e["site"] in site_ids and _valid_number(e["power"], "expansion_power_mw") and _valid_number(e["cooling"], "expansion_cooling_mwe")
                and _valid_number(e["racks"], "expansion_racks", True) and _valid_number(e["month"], "month", True)
                and (e["power"] > 0 or e["cooling"] > 0 or e["racks"] > 0))
    except (KeyError, TypeError):
        return False


def sanitize_state(sites: pd.DataFrame) -> list[str]:
    """Reset any stored numeric input that is missing, non-numeric, non-finite or outside its limit. Returns what was reset."""
    ss = st.session_state
    defaults = {**SCENARIO_KEYS, **VIEW_KEYS, **COST_DEFAULTS, **WIDGET_DEFAULTS}
    reset = []
    for key, name in KEY_LIMITS.items():
        if key in ss and not _valid_number(ss[key], name, key in INTEGER_KEYS):
            ss[key] = defaults[key]
            reset.append(key)
    for r in sites.itertuples():
        key = f"sg_{r.site_id}"
        if key in ss and not _valid_number(ss[key], "growth_pct"):
            ss[key] = float(r.annual_growth_pct)
            reset.append(key)
    if "warn_pct" in ss and "crit_pct" in ss and ss["crit_pct"] <= ss["warn_pct"]:
        ss["warn_pct"], ss["crit_pct"] = VIEW_KEYS["warn_pct"], VIEW_KEYS["crit_pct"]
        reset += ["warn_pct", "crit_pct"]
    if "expansions" in ss:
        site_ids = set(sites["site_id"])
        clean = [e for e in ss["expansions"] if _valid_expansion(e, site_ids)] if isinstance(ss["expansions"], list) else []
        if clean != ss["expansions"]:
            ss["expansions"] = clean
            reset.append("expansions")
    return sorted(set(reset))
