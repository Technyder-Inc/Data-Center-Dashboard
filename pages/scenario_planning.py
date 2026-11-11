import streamlit as st

from components import charts
from components.kpi_cards import recommendations_list, bullet_list, caption, chips, warning, html_table, month_text, risk_pill
from components.state import get_compare, GROWTH_MODES, apply_preset, get_results, mark_custom, reset_to_baseline, sync_thresholds
from components.styles import page_header, panel_title
from models.forecast import RESOURCE_META, effective_growth_pct
from models.scenarios import OUTCOME, PRESETS, risk_indicators, scenario_insights


def _sync_growth():
    st.session_state["growth_override"] = st.session_state["ui_sp_growth"]
    mark_custom()


def _controls(sites):
    ids = sites["site_id"].tolist()
    ss = st.session_state
    with st.container(border=True):
        panel_title("Scenario Presets")
        for name in PRESETS:
            st.button(name, key=f"sp_{name}", width="stretch", on_click=apply_preset, args=(name,),
                      type="primary" if ss["scenario_name"] == name else "secondary")
        st.button("Reset to Baseline", key="sp_reset", width="stretch", on_click=reset_to_baseline)
    with st.container(border=True):
        panel_title("Demand Growth")
        st.selectbox("Portfolio growth assumption", list(GROWTH_MODES.values()), key="growth_mode", on_change=mark_custom)
        if ss["growth_mode"] == GROWTH_MODES["adjust"]:
            st.slider("Adjustment to every site's rate (percentage points)", -10.0, 25.0, step=0.5, key="growth_adjust", on_change=mark_custom)
        elif ss["growth_mode"] == GROWTH_MODES["override"]:
            ss["ui_sp_growth"] = ss["growth_override"]
            st.slider("Annual growth applied to all sites (%)", 0.0, 60.0, step=0.5, key="ui_sp_growth", on_change=_sync_growth)
        st.multiselect("Sites with a site-specific growth override", ids, key="override_sites", on_change=mark_custom,
                       help="A site override always wins over the portfolio assumption.")
        for sid in ss["override_sites"]:
            st.number_input(f"{sid} annual growth (%)", -50.0, 100.0, step=0.5, key=f"sg_{sid}", on_change=mark_custom)
    with st.container(border=True):
        panel_title("Infrastructure Expansion")
        st.selectbox("Facility", ids, key="exp_site", on_change=mark_custom)
        a, b = st.columns(2)
        a.number_input("Power (MW)", 0.0, 50.0, step=0.5, key="exp_power", on_change=mark_custom)
        b.number_input("Cooling (MWe)", 0.0, 50.0, step=0.5, key="exp_cooling", on_change=mark_custom)
        c, d = st.columns(2)
        c.number_input("Racks", 0, 2000, step=10, key="exp_racks", on_change=mark_custom)
        d.number_input("Activation month", 0, 36, step=1, key="exp_month", on_change=mark_custom)
    with st.container(border=True):
        panel_title("Efficiency, Budget, Thresholds")
        st.slider("Operational efficiency: demand reduction (%)", 0, 30, key="efficiency", on_change=mark_custom,
                  help="Applied equally to power, cooling and rack demand (documented simplification).")
        st.number_input("Capital investment budget (USD millions)", 0.0, 1000.0, step=5.0, key="budget", on_change=mark_custom)
        st.checkbox("Fund prioritized planned projects within budget", key="fund_projects", on_change=mark_custom)
        st.slider("Warning threshold (%)", 50, 99, key="warn_pct", on_change=lambda: (sync_thresholds("warn_pct"), mark_custom()))
        st.slider("Critical threshold (%)", 51, 100, key="crit_pct", on_change=lambda: (sync_thresholds("crit_pct"), mark_custom()))


def render():
    r, base = get_results()
    p, pf, bp = r.params, r.portfolio, base.portfolio
    H = p.horizon
    page_header("Scenario Planning", "Adjust assumptions and compare the scenario against the baseline")
    left, right = st.columns([2, 5])
    with left:
        _controls(r.sites)
    with right:
        with st.container(border=True):
            panel_title(f"Active Scenario: {p.name}")
            g = effective_growth_pct(r.sites, p)
            mode_txt = {"site": "Dataset site rates", "adjust": f"Dataset rates {p.growth_value_pct:+g} pts", "override": f"All sites {p.growth_value_pct:g}%"}[p.growth_mode]
            chips([("Horizon", f"{H} months"), ("Growth", mode_txt),
                   ("Site overrides", ", ".join(f"{k} {v:g}%" for k, v in p.site_growth_overrides.items()) or "none"),
                   ("Efficiency", f"-{p.efficiency_pct:g}% demand"), ("Budget", f"${p.budget_usd_m:g}M"),
                   ("Planned projects", "funded within budget" if p.fund_planned_projects else "not applied"),
                   ("Thresholds", f"{p.warn_pct:g}% / {p.critical_pct:g}%")])
            exp_txt = [f"{e.site_id}: +{e.power_mw:g} MW power, +{e.cooling_mwe:g} MWe cooling, +{e.racks:g} racks from month {e.month} ({e.source})" for e in r.applied_expansions]
            chips([("Expansions", "; ".join(exp_txt) or "none")])
            caption("Effective annual growth by site: " + ", ".join(f"{k} {v:.1f}%" for k, v in g.items()))
        for w in r.warnings:
            warning(w)

        with st.container(border=True):
            panel_title("Before vs After: Portfolio")
            rows = []
            for res, meta in RESOURCE_META.items():
                u = meta["unit"]
                def f(k, fmt="{:,.1f}"):
                    return fmt.format(bp[k]) + " to " + fmt.format(pf[k])
                rows.append([f"<b>{meta['label']}</b> ({u})", f(f"{res}_horizon_capacity"), f(f"{res}_horizon_demand"),
                             f(f"{res}_horizon_util_pct", "{:.1f}%"), f(f"{res}_horizon_headroom"),
                             month_text(bp["aggregate_exhaustion_by_resource"][res], "None") + " to " + month_text(pf["aggregate_exhaustion_by_resource"][res], "None")])
            html_table([("Resource", False), (f"Capacity M{H} (base to scenario)", True), (f"Demand M{H}", True), (f"Utilization M{H}", True),
                        (f"Headroom M{H}", True), ("Aggregate exhaustion", True)], rows)
            st.session_state.setdefault("ui_sp_res", "Power")
            res_label = st.segmented_control("Resource", ["Power", "Cooling", "Racks"], key="ui_sp_res", label_visibility="collapsed") or "Power"
            c1, c2 = st.columns(2)
            c1.plotly_chart(charts.before_after(base.portfolio_series, r.portfolio_series, res_label.lower(), p), width="stretch")
            c2.plotly_chart(charts.peak_comparison(base.site_summary, r.site_summary, p), width="stretch")

        with st.container(border=True):
            panel_title("Revised Exhaustion Timing and Risk by Site")
            b = base.site_summary.set_index("site_id")
            rows, hl = [], set()
            for i, s in enumerate(r.site_summary.itertuples()):
                bs = b.loc[s.site_id]
                rows.append([f"<b>{s.site_id}</b>", f"{bs['first_limiting_resource'].title()}: {month_text(bs['earliest_exhaustion_month'], 'None')}",
                             f"{s.first_limiting_resource.title()}: {month_text(s.earliest_exhaustion_month, 'None')}",
                             f"{bs['peak_util_pct']:.1f}%", f"{s.peak_util_pct:.1f}%", risk_pill(bs["risk_level"]), risk_pill(s.risk_level)])
                if s.site_id == pf["earliest_site"]:
                    hl.add(i)
            html_table([("Site", False), ("Baseline first limit", False), ("Scenario first limit", False), ("Baseline peak", True), ("Scenario peak", True),
                        ("Baseline risk", False), ("Scenario risk", False)], rows, hl)

        with st.container(border=True):
            panel_title(f"Scenario Comparison (M{H} Outlook)")
            rows = []
            for c in get_compare().itertuples():
                tone = OUTCOME[c.risk][1]
                rows.append([("<b>" + c.scenario + "</b>") if c.scenario == p.name else c.scenario, f"+{c.capacity_added_mw:.1f} MW",
                             f"{c.utilization_pct:.1f}%", f"<span class='t-{'red' if c.headroom_mw < 0 else 'green'}'>{c.headroom_mw:+.1f} MW</span>",
                             month_text(c.earliest_month, "None"), month_text(c.aggregate_month, "None"), f"${c.cost_usd_m:.1f}M",
                             f"<span class='pill pill-{tone}'>{c.outcome}</span>"])
            html_table([("Scenario", False), ("Capacity added", True), ("Utilization", True), ("Headroom", True),
                        ("First site limit", False), ("Aggregate exhaustion", False), ("Capital", True), ("Outcome", False)], rows)
            caption("Presets at default settings for the active horizon, thresholds and budget. The active scenario above may differ if you customized controls.")
        r1, r2 = st.columns(2)
        with r1, st.container(border=True):
            panel_title("Risk Indicators")
            html_table([("Indicator", False), ("Level", False), ("Evidence", False)],
                       [[n, risk_pill(lv), ev] for n, lv, ev in risk_indicators(r)])
        with r2, st.container(border=True):
            panel_title("Recommended Actions")
            recommendations_list(r.recommendations[:4])

        c1, c2 = st.columns(2)
        with c1, st.container(border=True):
            panel_title("Capacity Gained and Budget")
            gain = {res: pf[f"{res}_horizon_capacity"] - bp[f"{res}_horizon_capacity"] for res in RESOURCE_META}
            bullet_list([f"{RESOURCE_META[k]['label']}: +{v:,.1f} {RESOURCE_META[k]['unit']} by month {H}" for k, v in gain.items()])
            used = r.total_investment_usd_m
            st.progress(min(used / p.budget_usd_m, 1.0) if p.budget_usd_m > 0 else (1.0 if used else 0.0))
            caption(f"Budget consumption: ${used:.1f}M of ${p.budget_usd_m:.1f}M ({100 * used / p.budget_usd_m if p.budget_usd_m else 0:.0f}%). "
                       f"Remaining: ${p.budget_usd_m - used:.1f}M. Manual expansion ${r.manual_cost_usd_m:.1f}M; funded planned projects ${r.funded_cost_usd_m:.1f}M.")
            caption(f"Remaining electrical headroom at month {H}: {pf['power_horizon_headroom']:.1f} MW (baseline {bp['power_horizon_headroom']:.1f} MW).")
        with c2, st.container(border=True):
            panel_title("Scenario Insights")
            bullet_list(scenario_insights(base, r))
