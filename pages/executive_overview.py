import pandas as pd
import streamlit as st

from components import charts
from components.kpi_cards import chips, html_table, icon_kpi, risk_pill, simple_recs, util_cell
from components.editors import assumptions_edited
from components.state import get_results, sites_edited
from components.styles import GREEN, BLUE, page_header, panel_title
from models.forecast import RESOURCE_META


def render():
    r, base = get_results()
    p, pf, ss = r.params, r.portfolio, r.site_summary
    H = p.horizon
    page_header("Executive Overview", "Portfolio capacity, utilization, and forecast across six data centers")

    ex = f"{pf['earliest_month']} Months" if pf["earliest_month"] is not None else f"> {H} Months"
    planned = bool(p.expansions)
    gain = pf["power_horizon_capacity"] - base.portfolio["power_horizon_capacity"]
    before = base.portfolio["earliest_month"]
    subs = ["", "", "", "", ""]
    if planned:
        subs[0] = (f"{pf['power_horizon_capacity']:.1f} MW at M{H} ({gain:+.1f})" if abs(gain) > 1e-9
                   else f"No added power by M{H}")
        subs[2] = f"{pf['power_horizon_util_pct']:.1f}% at month {H}"
        subs[4] = f"Baseline: {before} Months" if before is not None else f"Baseline: > {H} Months"
    cards = [
        icon_kpi("server", "Total Power Capacity", f"{pf['power_month0_capacity']:.1f} MW", sub=subs[0], tall=planned),
        icon_kpi("bolt", "Current Demand", f"{pf['power_month0_demand']:.1f} MW", sub=subs[1], tall=planned),
        icon_kpi("layers", "Utilization", f"{pf['power_month0_util_pct']:.1f}%", sub=subs[2], tall=planned),
        icon_kpi("trend", "36-Month Demand", f"{pf['power_demand_month36']:.1f} MW", sub=subs[3], tall=planned),
        icon_kpi("calendar", f"First Exhaustion: {pf['earliest_site']}" if pf["earliest_month"] is not None else "Portfolio Exhaustion",
                 ex, amber=True, sub=subs[4], tall=planned),
    ]
    for col, html in zip(st.columns(5), cards):
        col.markdown(html, unsafe_allow_html=True)
    constraint = (f"{pf['earliest_site']} {pf['earliest_resource']}, month {pf['earliest_month']}"
                  if pf['earliest_month'] is not None else f"None through month {H}")
    aggregate = (f"{pf['aggregate_resource']}, month {pf['aggregate_month']}"
                 if pf['aggregate_month'] is not None else f"None through month {H}")
    chips([("Active scenario", p.name), *([("Planned expansions", str(len(p.expansions)))] if planned else []),
           *([("Facility data", "edited")] if sites_edited() else []), *([("Assumptions", "edited")] if assumptions_edited() else []), ("Earliest site/resource exhaustion", constraint),
           ("Aggregate exhaustion", aggregate), ("Portfolio risk", pf["portfolio_risk"]),
           ("Sites approaching limits", f"{pf['sites_approaching']} / {pf['site_count']}"),
           *[(f"Power demand M{m}", f"{pf[f'power_demand_month{m}']:.1f} MW") for m in (12, 24, 36)]])
    with st.container(border=True):
        panel_title("Current Resource Capacity and Headroom (Active Scenario)")
        show_future = any(abs(pf[f"{res}_horizon_capacity"] - pf[f"{res}_month0_capacity"]) > 1e-9 for res in RESOURCE_META)
        rows = [[meta["label"], meta["unit"], f"{pf[f'{res}_month0_capacity']:,.1f}"]
                + ([f"{pf[f'{res}_horizon_capacity']:,.1f}"] if show_future else [])
                + [f"{pf[f'{res}_month0_demand']:,.1f}", f"{pf[f'{res}_month0_util_pct']:.1f}%", f"{pf[f'{res}_month0_headroom']:,.1f}"]
                for res, meta in RESOURCE_META.items()]
        html_table([("Resource", False), ("Unit", False), ("Capacity", True)]
                   + ([(f"Capacity at month {H} (with planned expansions)", True)] if show_future else [])
                   + [("Demand / occupied", True), ("Utilization / occupancy", True), ("Headroom", True)], rows)
    st.write("")

    used, cap = pf["power_month0_demand"], pf["power_month0_capacity"]
    left, right = st.columns([5, 3])
    with left, st.container(border=True):
        panel_title("Portfolio Power Demand Forecast")
        st.plotly_chart(charts.portfolio_forecast(r.portfolio_series, pf, p, r.applied_expansions), width="stretch")
    with right:
        with st.container(border=True):
            panel_title("Current Capacity Utilization (Power)")
            c1, c2 = st.columns([1, 1])
            c1.plotly_chart(charts.utilization_donut(used, cap, "MW"), width="stretch")
            c2.markdown(
                f"<div class='legend-lines'><div><i style='background:{GREEN}'></i>Used: {used:.1f} MW ({100 * used / cap:.1f}%)</div>"
                f"<div><i style='background:{BLUE}'></i>Available: {cap - used:.1f} MW ({100 * (cap - used) / cap:.1f}%)</div></div>", unsafe_allow_html=True)
        with st.container(border=True):
            panel_title("Portfolio Insights", "info")
            agg = pf["aggregate_exhaustion_by_resource"]["power"]
            n = pf["sites_approaching"]
            items = [
                f"Portfolio at {100 * used / cap:.1f}% utilization ({used:.1f} of {cap:.1f} MW)",
                f"Demand projected to reach {pf['power_horizon_capacity']:.1f} MW in ~ {agg} months" if agg is not None
                else f"Demand stays within {pf['power_horizon_capacity']:.1f} MW through {H} months",
                f"{n} sites reach at least {p.warn_pct:g}% utilization within months 0 to {H}",
                "Expansion or demand management recommended" if pf["portfolio_risk"] != "Low" else "No expansion needed within the forecast period",
            ]
            st.markdown("<ul class='insights'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>", unsafe_allow_html=True)

    bl, br = st.columns([2, 1])
    with bl, st.container(border=True):
        panel_title("Facility Capacity Summary")
        a = r.analysis
        rows = []
        for s in ss.itertuples():
            pw = a[(a["site_id"] == s.site_id) & (a["resource"] == "power")].iloc[0]
            u = s.power_util_month0_pct
            ex = f"&gt; {H} Months" if pd.isna(s.earliest_exhaustion_month) else f"{int(s.earliest_exhaustion_month)} Months"
            rows.append([f"<b>{s.site_id}</b>", s.location, f"{pw['month0_capacity']:.1f}", f"{pw['month0_demand']:.1f}",
                         util_cell(u, p.warn_pct), f"{s.power_demand_month36_mw:.1f}", ex, risk_pill(s.risk_level)])
        html_table([("Site", False), ("Location", False), ("Power Capacity (MW)", True), ("Current Demand (MW)", True), ("Utilization", True),
                    ("36-Month Demand (MW)", True), ("Exhaustion (Est.)", True), ("Risk", True)], rows, nowrap=True)
    with br, st.container(border=True):
        panel_title("Top Recommendations", "target")
        simple_recs([x["detail"] for x in r.recommendations[:3]])
