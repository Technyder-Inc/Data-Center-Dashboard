import streamlit as st

from components import charts
from components.kpi_cards import caption, text, warning, chips, html_table, icon_kpi, month_text, recommendations_list, risk_pill
from components.state import get_assumptions, get_results, mark_custom
from utils.validation import LIMITS
from components.styles import page_header, panel_title
from models.capital import expansion_cost
from utils import exports


REC_PAGE_SIZE = 5


def render():
    r, _ = get_results()
    p, pf = r.params, r.portfolio
    H = p.horizon
    page_header("Executive Decisions", "Capital planning, investment prioritization, and recommendations")
    caption("Illustrative cost assumptions only. They are not engineering or market cost claims, and no financial ROI is inferred.")

    with st.container(border=True):
        panel_title("Capital Cost Assumptions (illustrative, USD millions)")
        a, b, c, d = st.columns(4)
        a.number_input("Cost per additional MW (power)", *LIMITS["cost_per_mw"], step=0.5, key="cost_power", help="USD millions per MW")
        b.number_input("Cost per MWe of cooling", *LIMITS["cost_per_mwe"], step=0.25, key="cost_cooling", help="USD millions per MW-equivalent")
        c.number_input("Cost per additional rack", *LIMITS["cost_per_rack"], step=0.005, format="%.3f", key="cost_rack", help="USD millions per rack")
        d.number_input("Investment budget", *LIMITS["budget_usd_m"], step=5.0, key="budget", on_change=mark_custom, help="USD millions")

    used = r.total_investment_usd_m
    remaining = p.budget_usd_m - used
    proposed_all = r.manual_cost_usd_m + r.projects["cost_usd_m"].sum() if len(r.projects) else r.manual_cost_usd_m
    neg = remaining < -1e-9
    for col, html in zip(st.columns(5), [
        icon_kpi("coins", "Investment Budget", f"${p.budget_usd_m:,.1f}M", sub=f"Scenario: {p.name}"),
        icon_kpi("trend", "Committed in Scenario", f"${used:,.1f}M", tone="red" if neg else "",
                 sub=f"Manual ${r.manual_cost_usd_m:.1f}M + funded ${r.funded_cost_usd_m:.1f}M"),
        icon_kpi("layers", "Remaining Budget", f"${remaining:,.1f}M", tone="red" if neg else "green",
                 sub="Budget exceeded" if neg else "Available after commitments"),
        icon_kpi("server", "All Planned Projects", f"${r.projects['cost_usd_m'].sum() if len(r.projects) else 0:,.1f}M",
                 sub=f"{len(r.projects)} projects; incl. manual ${proposed_all:,.1f}M"),
        icon_kpi("bolt", f"Electrical Headroom M{H}", f"{pf['power_horizon_headroom']:.1f} MW", tone="red" if pf["power_horizon_headroom"] < 0 else "green",
                 sub=f"Capacity {pf['power_horizon_capacity']:.1f} MW; demand {pf['power_horizon_demand']:.1f} MW"),
    ]):
        col.markdown(html, unsafe_allow_html=True)
    for w in r.warnings:
        if "budget" in w.lower() or "exceeds" in w.lower():
            warning(w)
    st.write("")

    with st.container(border=True):
        panel_title("Investment Prioritization")
        pr = r.projects
        if p.fund_planned_projects:
            caption("Funding selection is applied to the forecast in this scenario.")
        else:
            caption("Funding selection shows what the budget would fund. It is applied to the forecast only when planned-project funding is enabled (Budget-Constrained preset).")
        if len(pr):
            caption("After-project exhaustion and headroom are hypothetical for each candidate, including unfunded projects. Headroom uses the limiting resource's unit (MW, MWe, or racks).")
            rows = []
            for x in pr.itertuples():
                tone = "green" if x.funding_status == "Funded" else "grey"
                rows.append([f"{x.priority_rank}", f"<b>{x.site_id}</b>", f"{x.priority_score:.1f}", x.limiting_resource.title() + ": " + month_text(x.exhaustion_month_before, "no exhaustion"),
                             risk_pill(x.risk_level), f"+{x.power_mw:g} MW / +{x.cooling_mwe:g} MWe / +{x.racks:g}", f"Month {x.activation_month}"
                             + (" <span class='t-red'>(after exhaustion)</span>" if x.activation_after_exhaustion else ""),
                             f"${x.cost_usd_m:,.1f}M", f"<span class='pill pill-{tone}'>{x.funding_status}</span>", month_text(x.exhaustion_month_after, "None"),
                             f"{x.limiting_resource_headroom_before:,.1f} to {x.limiting_resource_headroom_after:,.1f}"])
            html_table([("Rank", True), ("Site", False), ("Score", True), ("Limiting resource: exhaustion", False), ("Risk", False),
                        ("Gain (MW / MWe / racks)", False), ("Activation", False), ("Cost", True), ("Status", False),
                        ("Exhaustion after", False), (f"Headroom M{H}", False)], rows)
            avail = max(p.budget_usd_m - r.manual_cost_usd_m, 0.0)
            st.plotly_chart(charts.project_costs(pr, avail), width="stretch")
            funded = pr[pr["funding_status"] == "Funded"]
            chips([("Funded", f"{len(funded)} projects, ${funded['cost_usd_m'].sum():.1f}M"),
                   ("Unfunded", f"{(pr['funding_status'] == 'Unfunded').sum()} projects, ${pr.loc[pr['funding_status'] == 'Unfunded', 'cost_usd_m'].sum():.1f}M"),
                   ("Capacity gained if funded", f"{funded['power_mw'].sum():g} MW, {funded['cooling_mwe'].sum():g} MWe, {funded['racks'].sum():g} racks")])
        else:
            st.info("No planned projects in the dataset.")
        with st.expander("Scoring methodology"):
            text(
                "Each project scores 0 to 100 using fixed weights, evaluated on the active scenario without the funded planned projects:\n\n"
                + "\n".join(f"- **{k.replace('_', ' ').title()}** weight {int(v * 100)}%" for k, v in get_assumptions().weights().items())
                + "\n\nTiming = 100 x (1 - exhaustion month / horizon), 0 if no exhaustion. Peak utilization = (peak% - 50) / 50 capped to 0 to 100. "
                "Risk level: Low 0, Medium 40, High 70, Critical 100. Resource fit = 100 if the project adds capacity to the site's first limiting resource. "
                "Cost = 100 x (1 - cost / highest project cost). Ties break by site ID. Selection walks the ranking and funds each project that fits the remaining budget."
            )

    c1, c2 = st.columns([3, 2])
    with c1, st.container(border=True):
        panel_title("Executive Recommendations", "target")
        recs = r.recommendations
        pages = max(1, -(-len(recs) // REC_PAGE_SIZE))
        page = min(max(int(st.session_state.get("ui_rec_page") or st.session_state.get("ui_rec_last", 1)), 1), pages)
        st.session_state["ui_rec_page"] = str(page)
        st.session_state["ui_rec_last"] = page
        recommendations_list(recs[(page - 1) * REC_PAGE_SIZE:page * REC_PAGE_SIZE])
        if pages > 1:
            info_col, pager_col = st.columns([3, 2], vertical_alignment="center")
            info_col.markdown(f"<span style='color:#9fb0d6;font-size:.85rem'>Showing {(page - 1) * REC_PAGE_SIZE + 1} to {min(page * REC_PAGE_SIZE, len(recs))} of {len(recs)}</span>", unsafe_allow_html=True)
            pager_col.segmented_control("Page", [str(n) for n in range(1, pages + 1)], key="ui_rec_page", label_visibility="collapsed")
        caption(f"Rules are deterministic Python over modeled results. Schedule assumes a {get_assumptions().lead_time_months}-month commissioning lead time.")
    with c2, st.container(border=True):
        panel_title("Manual Expansion Costing")
        if r.applied_expansions and any(e.source == "manual" for e in r.applied_expansions):
            for e in [e for e in r.applied_expansions if e.source == "manual"]:
                text(f"**{e.site_id}**: +{e.power_mw:g} MW, +{e.cooling_mwe:g} MWe, +{e.racks:g} racks, active month {e.month}")
                text(f"Cost ${expansion_cost(e, r.costs):,.1f}M against ${p.budget_usd_m:,.1f}M budget")
        else:
            caption("No manual expansion defined. Configure one in Scenario Planning.")

    with st.container(border=True):
        panel_title("Exports (active scenario)")
        cols = st.columns(4)
        specs = [("Facility capacity data", "facility", exports.facility_frame), ("Monthly capacity forecast", "forecast", exports.forecast_frame),
                 ("Scenario assumptions and results", "scenario", exports.scenario_frame), ("Capital investment comparison", "capital", exports.capital_frame)]
        for col, (label, kind, fn) in zip(cols, specs):
            col.download_button(f"Download: {label}", exports.to_csv_bytes(fn(r)), file_name=exports.filename(r, kind), mime="text/csv", key=f"dl_{kind}", width="stretch")
        caption("Unit-bearing column names (MW, MWe, racks, USD millions). Values match the dashboard for the active scenario and horizon.")
