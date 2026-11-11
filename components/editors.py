"""Modal editors for the facility dataset and the model assumptions that were previously hard-coded."""
from dataclasses import replace

import streamlit as st

from components import state
from models.assumptions import DEFAULT_ASSUMPTIONS, Assumptions, validate_assumptions
from models.editing import EDITABLE_COLUMNS, apply_site_edits, matches_dataset
from utils.validation import LIMITS

NUM = st.column_config.NumberColumn


@st.dialog("Edit facility data (synthetic)", width="large")
def edit_facility_data() -> None:
    st.caption("Change any value, then Save. Facility IDs are fixed. Entries are validated exactly like the CSV: capacities must be above zero, "
               "values must not be negative, and rack counts and months must be whole numbers. Project cost and risk status are recalculated on save.")
    current = state.get_sites()
    edited = st.data_editor(
        current[["site_id", *EDITABLE_COLUMNS]], hide_index=True, num_rows="fixed", width="stretch", key="fac_editor", disabled=["site_id"],
        column_config={
            "site_id": "Site", "site_name": "Name", "location": "Location",
            "electrical_capacity_mw": NUM("Electrical capacity (MW)", min_value=0.01, max_value=LIMITS["capacity_mw"][1], format="%.2f"),
            "electrical_demand_mw": NUM("Electrical demand (MW)", min_value=0.0, max_value=LIMITS["demand_mw"][1], format="%.2f"),
            "cooling_capacity_mwe": NUM("Cooling capacity (MWe)", min_value=0.01, max_value=LIMITS["capacity_mw"][1], format="%.2f"),
            "cooling_demand_mwe": NUM("Cooling load (MWe)", min_value=0.0, max_value=LIMITS["demand_mw"][1], format="%.2f"),
            "rack_capacity": NUM("Rack capacity", min_value=1, max_value=LIMITS["rack_capacity"][1], step=1, format="%d"),
            "occupied_racks": NUM("Occupied racks", min_value=0, max_value=LIMITS["occupied_racks"][1], step=1, format="%d"),
            "annual_growth_pct": NUM("Annual growth (%)", min_value=LIMITS["growth_pct"][0], max_value=LIMITS["growth_pct"][1], format="%.1f"),
            "planned_power_expansion_mw": NUM("Planned power (MW)", min_value=0.0, max_value=LIMITS["expansion_power_mw"][1], format="%.2f"),
            "planned_cooling_expansion_mwe": NUM("Planned cooling (MWe)", min_value=0.0, max_value=LIMITS["expansion_cooling_mwe"][1], format="%.2f"),
            "planned_additional_racks": NUM("Planned racks", min_value=0, max_value=LIMITS["expansion_racks"][1], step=1, format="%d"),
            "expansion_activation_month": NUM("Activation month", min_value=0, max_value=LIMITS["month"][1], step=1, format="%d"),
        },
    )
    save, reset, cancel = st.columns(3)
    if save.button("Save changes", type="primary", width="stretch"):
        df, errors, warnings = apply_site_edits(current, edited)
        if errors:
            for e in errors:
                st.error(e)
        else:
            if matches_dataset(df, state.load_sites()):
                st.session_state.pop("sites_override", None)
            else:
                st.session_state["sites_override"] = df
            state.reset_site_growth_defaults(df)
            st.session_state["ui_edit_notice"] = warnings
            st.rerun()
    if reset.button("Reset to dataset", width="stretch", disabled=not state.sites_edited()):
        st.session_state.pop("sites_override", None)
        state.reset_site_growth_defaults(state.load_sites())
        st.rerun()
    if cancel.button("Cancel", width="stretch"):
        st.rerun()


def _num(container, label, value, step, key, minimum, maximum, integer=False):
    return container.number_input(label, min_value=minimum, max_value=maximum, value=int(value) if integer else float(value),
                                  step=int(step) if integer else float(step), key=key)


@st.dialog("Edit model assumptions", width="large")
def edit_assumptions() -> None:
    st.caption("These values were fixed in the code. Scenario presets use them when you click the preset again; "
               "ranking weights, lead times and what-if values apply immediately.")
    a = state.get_assumptions()
    sites = state.get_sites()["site_id"].tolist()
    st.markdown("**Scenario presets**")
    c1, c2 = st.columns(2)
    growth = _num(c1, "High Growth annual rate (%)", a.high_growth_pct, 1.0, "as_growth", *LIMITS["portfolio_growth_pct"])
    eff = _num(c2, "Efficiency Optimization demand reduction (%)", a.efficiency_pct, 1.0, "as_eff", *LIMITS["efficiency_pct"])
    st.markdown("**Infrastructure Expansion preset**")
    c1, c2, c3, c4, c5 = st.columns(5)
    site = c1.selectbox("Facility", sites, index=sites.index(a.expansion_site) if a.expansion_site in sites else 0, key="as_site")
    power = _num(c2, "Power (MW)", a.expansion_power_mw, 0.5, "as_pw", *LIMITS["expansion_power_mw"])
    cool = _num(c3, "Cooling (MWe)", a.expansion_cooling_mwe, 0.5, "as_cl", *LIMITS["expansion_cooling_mwe"])
    racks = _num(c4, "Racks", a.expansion_racks, 10, "as_rk", *LIMITS["expansion_racks"], integer=True)
    month = _num(c5, "Activation month", a.expansion_month, 1, "as_mo", 0, 36, integer=True)
    st.markdown("**Investment ranking (weights must total 100)**")
    c1, c2, c3, c4, c5 = st.columns(5)
    w = [_num(c, lbl, v, 5.0, k, 0.0, 100.0) for c, lbl, v, k in (
        (c1, "Timing (%)", a.weight_timing, "as_w1"), (c2, "Peak utilization (%)", a.weight_peak, "as_w2"), (c3, "Risk level (%)", a.weight_risk, "as_w3"),
        (c4, "Resource fit (%)", a.weight_fit, "as_w4"), (c5, "Cost (%)", a.weight_cost, "as_w5"))]
    c1, c2, c3 = st.columns(3)
    s_med = _num(c1, "Risk score: Medium", a.score_medium, 5.0, "as_s1", 0.0, 100.0)
    s_high = _num(c2, "Risk score: High", a.score_high, 5.0, "as_s2", 0.0, 100.0)
    s_crit = _num(c3, "Risk score: Critical", a.score_critical, 5.0, "as_s3", 0.0, 100.0)
    st.markdown("**Timing and display**")
    c1, c2, c3, c4, c5 = st.columns(5)
    lead = _num(c1, "Commissioning lead time (months)", a.lead_time_months, 1, "as_ld", 0, 36, integer=True)
    imm = _num(c2, "Immediate-attention window (months)", a.immediate_months, 1, "as_im", 0, 36, integer=True)
    caution = _num(c3, "Amber colour starts at (%)", a.caution_pct, 5.0, "as_ca", 1.0, 99.0)
    wi_eff = _num(c4, "What-if efficiency (%)", a.whatif_efficiency_pct, 1.0, "as_we", 0.5, 99.0)
    wi_delay = _num(c5, "What-if delay (months)", a.whatif_delay_months, 1, "as_wd", 1, 36, integer=True)
    save, reset, cancel = st.columns(3)
    if save.button("Save assumptions", type="primary", width="stretch"):
        new = replace(a, high_growth_pct=growth, efficiency_pct=eff, expansion_site=site, expansion_power_mw=power, expansion_cooling_mwe=cool,
                      expansion_racks=racks, expansion_month=month, weight_timing=w[0], weight_peak=w[1], weight_risk=w[2], weight_fit=w[3],
                      weight_cost=w[4], score_medium=s_med, score_high=s_high, score_critical=s_crit, lead_time_months=lead,
                      immediate_months=imm, caution_pct=caution, whatif_efficiency_pct=wi_eff, whatif_delay_months=wi_delay)
        errors = validate_assumptions(new, sites)
        if errors:
            for e in errors:
                st.error(e)
        else:
            st.session_state["assumptions"] = new
            st.rerun()
    if reset.button("Restore defaults", width="stretch", disabled=a == DEFAULT_ASSUMPTIONS):
        st.session_state.pop("assumptions", None)
        st.rerun()
    if cancel.button("Cancel", width="stretch"):
        st.rerun()


def assumptions_edited() -> bool:
    return state.get_assumptions() != Assumptions()
