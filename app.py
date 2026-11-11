"""Six-Site Data Center Capacity Planning and Executive Decision Simulator (synthetic demonstration)."""
import streamlit as st

from components import state
from components.expansions import expansion_list
from components.styles import inject_css, notice_bar
from models.scenarios import baseline_like
from pages import capacity_forecasting, executive_decisions, executive_overview, scenario_planning
from utils.validation import HORIZONS, LIMITS, ValidationError

st.set_page_config(page_title="Six-Site Capacity Simulator", page_icon=":material/dns:", layout="wide", initial_sidebar_state="auto")

sites = state.get_sites()
state.init_state(sites)
reset_inputs = state.sanitize_state(sites)
state.persist()
inject_css()
notice_bar()
if reset_inputs:
    st.warning("Some inputs were missing or outside their allowed range and were reset to defaults: " + ", ".join(reset_inputs))

pages = [
    st.Page(executive_overview.render, title="Executive Overview", icon=":material/home:", url_path="overview", default=True),
    st.Page(capacity_forecasting.render, title="Capacity Forecasting", icon=":material/show_chart:", url_path="forecasting"),
    st.Page(scenario_planning.render, title="Scenario Planning", icon=":material/tune:", url_path="scenarios"),
    st.Page(executive_decisions.render, title="Executive Decisions", icon=":material/work:", url_path="decisions"),
]
nav = st.navigation(pages, position="hidden")
nav_page = nav

def horizon_widget(container):
    container.selectbox("Forecast Horizon", HORIZONS, format_func=lambda m: f"{m} Months", key="horizon")


def growth_widget(container):
    growth_text = "Site rates" if st.session_state["growth_mode"] == state.GROWTH_MODES["site"] else f"{st.session_state['growth_override']:.0f}%"
    container.markdown(f"<div class='slider-label'><span>Annual Demand Growth</span><span>{growth_text}</span></div>", unsafe_allow_html=True)
    container.slider("Annual Demand Growth", *LIMITS["portfolio_growth_pct"], step=1.0, format="%.0f%%", key="growth_override", on_change=state.set_growth,
                     label_visibility="collapsed")


def expansion_widget(container):
    ss = st.session_state
    options = [state.exp_summary_label(), *state.EXP_RESOURCES]
    if ss.get("ui_exp_choice") not in options:
        ss["ui_exp_choice"] = options[0]
    container.selectbox("Infrastructure Expansion", options, key="ui_exp_choice")
    label = ss["ui_exp_choice"]
    if label in state.EXP_RESOURCES:
        key, unit, default, step = state.EXP_RESOURCES[label]
        is_racks = key == "exp_racks"
        ss.setdefault("sb_exp_site", "DC3")
        ss.setdefault("sb_exp_month", 0)
        ss.setdefault(f"sb_amt_{key}", int(default) if is_racks else float(default))
        container.selectbox("Facility", sites["site_id"].tolist(), key="sb_exp_site")
        c1, c2 = container.columns(2)
        lo, hi = LIMITS["expansion_racks"] if is_racks else LIMITS["expansion_power_mw" if key == "exp_power" else "expansion_cooling_mwe"]
        c1.number_input(f"Amount ({unit})", min_value=lo, max_value=hi, step=step, key=f"sb_amt_{key}")
        c2.number_input("Activation month", *LIMITS["month"], step=1, key="sb_exp_month")
        container.button("Add to plan", key="sb_add_exp", on_click=state.add_expansion_from_sidebar, width="stretch")
    expansion_list(container, "sb")


BRAND = (
    "<div class='brand'><svg width='42' height='42' viewBox='0 0 24 24' fill='none'>"
    "<rect x='3' y='3.5' width='18' height='5' rx='1.3' fill='#a9b8de'/><rect x='3' y='9.5' width='18' height='5' rx='1.3' fill='#a9b8de'/><rect x='3' y='15.5' width='18' height='5' rx='1.3' fill='#a9b8de'/>"
    "<circle cx='6.5' cy='6' r='.9' fill='#0c1533'/><circle cx='6.5' cy='12' r='.9' fill='#0c1533'/><circle cx='6.5' cy='18' r='.9' fill='#0c1533'/>"
    "</svg><div>Six-Site<br>Data Center<br>Capacity Simulator</div></div>"
)
st.markdown(f"<style>.st-key-nav_{pages.index(nav_page)} a {{ background:#2f6fe4 !important; color:#fff !important; font-weight:600; }} .st-key-nav_{pages.index(nav_page)} a * {{ color:#fff !important; }}</style>", unsafe_allow_html=True)
cur = st.session_state["scenario_name"]
assump = state.get_assumptions()
quick = [("Baseline (Current)", "Baseline"),
         (f"High Growth ({assump.high_growth_pct:g}%)", "High Growth"),
         ("Infrastructure Expansion", "Infrastructure Expansion"),
         (f"Efficiency Optimization (-{assump.efficiency_pct:g}%)", "Efficiency Optimization"),
         ("Budget-Constrained", "Budget-Constrained")]

with st.sidebar:
    st.markdown(BRAND, unsafe_allow_html=True)
    for i, pg in enumerate(pages):
        with st.container(key=f"nav_{i}"):
            st.page_link(pg)
    st.markdown("<div class='side-h'>Simulation Controls</div>", unsafe_allow_html=True)
    horizon_widget(st)
    growth_widget(st)
    expansion_widget(st)
    impact_slot = st.empty()
    st.markdown("<div class='side-h'>Quick Scenarios</div>", unsafe_allow_html=True)
    for label, name in quick:
        st.button(label, key=f"side_{name}", width="stretch", on_click=state.apply_preset, args=(name,), type="primary" if cur == name else "secondary")

try:
    params = state.params_from_state()
    costs = state.costs_from_state()
    st.session_state["_result"] = state.run_main(params, costs, sites, assump)
    st.session_state["_baseline"] = state.run_main(baseline_like(params), costs, sites, assump)
    note = state.expansion_impact(st.session_state["_result"], st.session_state["_baseline"])
    if note:
        impact_slot.caption(note)
except ValidationError as exc:
    st.error("Invalid inputs: " + "; ".join(exc.errors))
    st.button("Reset to Baseline", key="err_reset", on_click=state.reset_to_baseline)
    st.stop()

nav.run()
