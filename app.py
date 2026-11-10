"""Six-Site Data Center Capacity Planning and Executive Decision Simulator (synthetic demonstration)."""
import streamlit as st

from components import state
from components.styles import inject_css, notice_bar
from models.scenarios import baseline_like, compare_presets, run_scenario
from pages import capacity_forecasting, executive_decisions, executive_overview, scenario_planning
from utils.validation import HORIZONS, ValidationError

st.set_page_config(page_title="Six-Site Capacity Simulator", page_icon=":material/dns:", layout="wide", initial_sidebar_state="expanded")

sites = state.load_sites()
state.init_state(sites)
state.persist()
inject_css()
notice_bar()

pages = [
    st.Page(executive_overview.render, title="Executive Overview", icon=":material/home:", url_path="overview", default=True),
    st.Page(capacity_forecasting.render, title="Capacity Forecasting", icon=":material/show_chart:", url_path="forecasting"),
    st.Page(scenario_planning.render, title="Scenario Planning", icon=":material/tune:", url_path="scenarios"),
    st.Page(executive_decisions.render, title="Executive Decisions", icon=":material/work:", url_path="decisions"),
]
nav = st.navigation(pages, position="hidden")

def horizon_widget(container):
    container.selectbox("Forecast Horizon", HORIZONS, format_func=lambda m: f"{m} Months", key="horizon")


def growth_widget(container):
    container.slider("Annual Demand Growth", 0.0, 60.0, step=1.0, format="%.0f%%", key="growth_override", on_change=state.set_growth,
                     help="15% shows the dataset's own site growth rates until you move the slider; any other value applies to all sites.")


def expansion_widget(container):
    st.session_state["ui_exp_choice"] = state.expansion_label()
    container.selectbox("Infrastructure Expansion", [*state.EXP_CHOICES, state.EXP_CUSTOM], key="ui_exp_choice", on_change=state.set_expansion)


BRAND = (
    "<div class='brand'><svg width='40' height='40' viewBox='0 0 24 24' fill='none' stroke='#9fb0d6' stroke-width='1.6'>"
    "<rect x='3' y='4' width='18' height='4' rx='1'/><rect x='3' y='10' width='18' height='4' rx='1'/><rect x='3' y='16' width='18' height='4' rx='1'/>"
    "</svg><div>Six-Site<br>Data Center<br>Capacity Simulator</div></div>"
)
cur = st.session_state["scenario_name"]
quick = [("Baseline (Current)", "Baseline", state.apply_preset, ("Baseline",), ":material/bar_chart:"),
         ("High Growth (25%)", "High Growth", state.apply_preset, ("High Growth",), ":material/trending_up:"),
         ("Add 1 MW (Site 3)", "Infrastructure Expansion", state.apply_quick_expansion, (), ":material/bolt:"),
         ("Optimize Utilization (-10%)", "Efficiency Optimization", state.apply_preset, ("Efficiency Optimization",), ":material/tune:")]

with st.sidebar:
    st.markdown(BRAND, unsafe_allow_html=True)
    for pg in pages:
        st.page_link(pg)
    st.markdown("<div class='side-h'>Simulation Controls</div>", unsafe_allow_html=True)
    horizon_widget(st)
    growth_widget(st)
    expansion_widget(st)
    st.markdown("<div class='side-h'>Quick Scenarios</div>", unsafe_allow_html=True)
    for label, name, fn, args, _icon in quick:
        st.button(label, key=f"side_{name}", width="stretch", on_click=fn, args=args, type="primary" if cur == name else "secondary")

try:
    params = state.params_from_state()
    costs = state.costs_from_state()
    st.session_state["_result"] = run_scenario(sites, params, costs)
    st.session_state["_baseline"] = run_scenario(sites, baseline_like(params), costs)
    st.session_state["_compare"] = compare_presets(sites, params, costs)
except ValidationError as exc:
    st.error("Invalid inputs: " + "; ".join(exc.errors))
    st.stop()

nav.run()
