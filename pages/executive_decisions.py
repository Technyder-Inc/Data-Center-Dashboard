import pandas as pd
import streamlit as st

from components import charts
from components.kpi_cards import caption, md, text, warning, chips, html_table, kpi_card, kpi_row, month_text, recommendations_list, risk_pill
from components.state import get_compare, get_results, mark_custom
from components.styles import page_header, panel_title
from models.scenarios import OUTCOME
from models.capital import LEAD_TIME_MONTHS, WEIGHTS, expansion_cost
from utils import exports


def render():
    r, _ = get_results()
    p, pf = r.params, r.portfolio
    H = p.horizon
    page_header("Executive Decisions", "Capital planning, investment prioritization, and recommendations")
    caption("Illustrative cost assumptions only. They are not engineering or market cost claims, and no financial ROI is inferred.")

    with st.container(border=True):
        panel_title("Capital Cost Assumptions (illustrative, USD millions)")
        a, b, c, d = st.columns(4)
        a.number_input("Cost per additional MW (power)", 0.0, 100.0, step=0.5, key="cost_power", help="USD millions per MW")
        b.number_input("Cost per MWe of cooling", 0.0, 100.0, step=0.25, key="cost_cooling", help="USD millions per MW-equivalent")
        c.number_input("Cost per additional rack", 0.0, 5.0, step=0.005, format="%.3f", key="cost_rack", help="USD millions per rack")
        d.number_input("Investment budget", 0.0, 1000.0, step=5.0, key="budget", on_change=mark_custom, help="USD millions")

    used = r.total_investment_usd_m
    remaining = p.budget_usd_m - used
    proposed_all = r.manual_cost_usd_m + r.projects["cost_usd_m"].sum() if len(r.projects) else r.manual_cost_usd_m
    kpi_row([
        kpi_card("Investment Budget", f"${p.budget_usd_m:,.1f}M", f"Scenario: {p.name}"),
        kpi_card("Committed in Scenario", f"${used:,.1f}M", f"Manual ${r.manual_cost_usd_m:.1f}M + funded projects ${r.funded_cost_usd_m:.1f}M", "red" if remaining < -1e-9 else "blue"),
        kpi_card("Remaining Budget", f"${remaining:,.1f}M", "Shortfall: budget exceeded" if remaining < -1e-9 else "Available after commitments", "red" if remaining < -1e-9 else "green"),
        kpi_card("All Planned Projects", f"${r.projects['cost_usd_m'].sum() if len(r.projects) else 0:,.1f}M", f"{len(r.projects)} projects; proposed total incl. manual ${proposed_all:,.1f}M", "amber"),
        kpi_card(f"Electrical Headroom M{H}", f"{pf['power_horizon_headroom']:.1f} MW", f"Capacity {pf['power_horizon_capacity']:.1f} MW; demand {pf['power_horizon_demand']:.1f} MW", "red" if pf["power_horizon_headroom"] < 0 else "green"),
    ])
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
                + "\n".join(f"- **{k.replace('_', ' ').title()}** weight {int(v * 100)}%" for k, v in WEIGHTS.items())
                + "\n\nTiming = 100 x (1 - exhaustion month / horizon), 0 if no exhaustion. Peak utilization = (peak% - 50) / 50 capped to 0 to 100. "
                "Risk level: Low 0, Medium 40, High 70, Critical 100. Resource fit = 100 if the project adds capacity to the site's first limiting resource. "
                "Cost = 100 x (1 - cost / highest project cost). Ties break by site ID. Selection walks the ranking and funds each project that fits the remaining budget."
            )

    with st.container(border=True):
        panel_title(f"What-If Analysis (M{H} Outcomes)")
        rows = []
        for c in get_compare().itertuples():
            tone = OUTCOME[c.risk][1]
            rows.append([c.scenario, f"+{c.capacity_added_mw:.1f} MW", f"<span class='t-{'red' if c.utilization_pct > 100 else 'green'}'>{c.utilization_pct:.1f}%</span>",
                         f"${c.cost_usd_m:.1f}M", f"<span class='pill pill-{tone}'>{c.outcome}</span>"])
        html_table([("Scenario", False), ("New capacity", True), (f"Utilization M{H}", True), ("Capital", True), ("Outcome", False)], rows)

    s1, s2 = st.columns([3, 2])
    with s1, st.container(border=True):
        panel_title("Site Forecast (Power, MW)")
        fcp = r.forecast[r.forecast["resource"] == "power"]
        trend = fcp[fcp["month"] % 6 == 0].sort_values("month").groupby("site_id")["demand"].apply(list)
        at = fcp.pivot(index="site_id", columns="month", values="demand")
        tbl = pd.DataFrame({"Site": at.index, "Current": at[0].values, "12M": at[12].values, "24M": at[24].values, "36M": at[36].values,
                            "Trend": [trend[s] for s in at.index]})
        tot = pd.DataFrame([{"Site": "Total", "Current": tbl["Current"].sum(), "12M": tbl["12M"].sum(), "24M": tbl["24M"].sum(), "36M": tbl["36M"].sum(),
                             "Trend": [float(fcp[fcp["month"] == m]["demand"].sum()) for m in range(0, 37, 6)]}])
        fmt = st.column_config.NumberColumn(format="%.1f")
        st.dataframe(pd.concat([tbl, tot], ignore_index=True), hide_index=True, width="stretch",
                     column_config={"Current": fmt, "12M": fmt, "24M": fmt, "36M": fmt, "Trend": st.column_config.LineChartColumn("Trend (0 to 36M)")})
    with s2, st.container(border=True):
        panel_title("Operational Risks (Top 3)")
        risky = [x for x in r.recommendations if x["severity"] in ("critical", "high")][:3] or r.recommendations[:3]
        lvl = {"critical": "Critical", "high": "High"}
        html_table([("Risk", False), ("Level", False)],
                   [[f"<b>{x['title']}</b><br><span class='kpi-sub'>{x['detail']}</span>", risk_pill(lvl.get(x["severity"], "Medium"))] for x in risky])

    funded_now = r.projects[r.projects["funding_status"] == "Funded"] if len(r.projects) else r.projects
    decision_basis = repr((p, r.costs, funded_now.to_dict("records")))
    if st.session_state.get("_decision_basis") != decision_basis:
        for key in list(st.session_state):
            if key.startswith("ui_req_") or key == "ui_approval":
                del st.session_state[key]
        st.session_state["_decision_basis"] = decision_basis
    d1, d2 = st.columns([3, 2])
    with d1, st.container(border=True):
        panel_title("Decision Requests")
        if len(funded_now):
            for x in funded_now.itertuples():
                st.checkbox(md(f"Approve {x.site_id} expansion: +{x.power_mw:g} MW, +{x.cooling_mwe:g} MWe, +{x.racks:g} racks, ${x.cost_usd_m:.1f}M, activation month {x.activation_month}"), key=f"ui_req_{x.site_id}")
        else:
            st.caption("No projects fit the budget.")
        choice = st.radio("Executive approval", ["Approve", "Approve with Conditions", "Defer", "Reject"], key="ui_approval", horizontal=True)
        picked = [x.site_id for x in funded_now.itertuples() if st.session_state.get(f"ui_req_{x.site_id}")]
        caption(f"Decision (this session only, not persisted): {choice}. Requests ticked: {', '.join(picked) or 'none'}.")
    with d2, st.container(border=True):
        panel_title("Recommendation")
        if len(funded_now):
            unf = r.projects[(r.projects["funding_status"] == "Unfunded") & r.projects["exhaustion_month_before"].notna()]
            msg = (f"Fund {', '.join(funded_now['site_id'])} (${funded_now['cost_usd_m'].sum():.1f}M of ${p.budget_usd_m:.1f}M budget). "
                   + (f"Earliest constraint: {pf['earliest_site']} {pf['earliest_resource']} in month {pf['earliest_month']}. " if pf["earliest_month"] is not None else "")
                   + (f"Unfunded sites with modeled exhaustion: {', '.join(unf['site_id'])}." if len(unf) else "No unfunded site exhausts within the horizon."))
            residual = funded_now[funded_now["exhaustion_month_after"].notna()]
            if len(residual):
                msg += " Funding does not eliminate all modeled exhaustion at " + ", ".join(residual.site_id) + "; review timing and residual resource constraints before approval."
            no_fit = funded_now[funded_now["resource_fit_score"] == 0]
            if len(no_fit):
                msg += " Projects at " + ", ".join(no_fit.site_id) + " do not add the limiting resource; revise their scope."
        else:
            msg = "No planned project fits the budget; increase the budget or reduce project scope."
        text(msg)

    c1, c2 = st.columns([3, 2])
    with c1, st.container(border=True):
        panel_title("Executive Recommendations")
        recommendations_list(r.recommendations)
        caption(f"Rules are deterministic Python over modeled results. Schedule assumes a {LEAD_TIME_MONTHS}-month commissioning lead time.")
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
