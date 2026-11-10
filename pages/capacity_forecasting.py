import pandas as pd
import streamlit as st

from components import charts
from components.kpi_cards import chips, html_table, month_text, risk_pill
from components.state import get_results
from components.styles import page_header, panel_title
from models.forecast import RESOURCE_META


def render():
    r, _ = get_results()
    p, ss, fc = r.params, r.site_summary, r.forecast
    ids = r.sites["site_id"].tolist()
    H = p.horizon
    page_header("Capacity Forecasting", "Facility-level and portfolio-level power, cooling, and rack forecasts")
    st.caption(f"Active scenario: **{p.name}** | Forecast months 0 to {H} | Expansion capacity is available from its activation month")

    c1, c2, c3 = st.columns([2, 3, 2])
    res_label = c1.segmented_control("Resource", ["Power", "Cooling", "Racks"], default="Power", key="ui_fc_res") or "Power"
    sel = c2.multiselect("Facilities", ids, default=ids, key="ui_fc_sites") or ids[:1]
    default_view = "Utilization (%)" if len(sel) > 1 else "Demand vs capacity"
    view = c3.radio("Chart view", ["Utilization (%)", "Demand vs capacity"], index=["Utilization (%)", "Demand vs capacity"].index(default_view),
                    key=f"ui_fc_view_{len(sel) > 1}", horizontal=True)
    res = res_label.lower()
    meta = RESOURCE_META[res]

    with st.container(border=True):
        panel_title(f"{meta['label']} Forecast: {', '.join(sel)}")
        st.plotly_chart(charts.site_forecast(fc, sel, res, view, p, r.applied_expansions, ids), width="stretch")
        st.caption("Red X: first month demand exceeds capacity. Blue diamond: expansion activation. Dashed amber/red lines: warning and exhaustion thresholds.")

    with st.container(border=True):
        panel_title("First Limiting Resource by Site")
        rows, hl = [], set()
        for i, s in enumerate(ss[ss["site_id"].isin(sel)].itertuples()):
            ex = month_text(s.earliest_exhaustion_month)
            warn = month_text(s.first_warning_month, "Not reached")
            basis = "first exhaustion" if s.limiting_basis == "exhaustion" else "highest peak utilization (no exhaustion)"
            rows.append([f"<b>{s.site_id}</b>", s.first_limiting_resource.title(), basis, ex, warn,
                         f"{s.peak_util_pct:.1f}% ({s.peak_resource}, month {s.peak_month})", risk_pill(s.risk_level)])
            if s.site_id == r.portfolio["earliest_site"]:
                hl.add(i)
        html_table([("Site", False), ("First limiting resource", False), ("Basis", False), ("Exhaustion", False),
                    (f"First reaches {p.warn_pct:g}%", False), ("Peak utilization", False), ("Risk", False)], rows, hl)
        pf = r.portfolio
        if pf["earliest_month"] is not None:
            tail = f" Portfolio aggregate {pf['aggregate_resource']} is exhausted in month {pf['aggregate_month']}." if pf["aggregate_month"] is not None else f" Aggregate portfolio capacity is not exhausted within {H} months."
            st.warning(f"Earliest constraint: {pf['earliest_site']} {pf['earliest_resource']} in month {pf['earliest_month']}.{tail} Site limits bind before the portfolio aggregate.")

    with st.container(border=True):
        panel_title(f"Baseline vs Projected: {meta['label']} ({meta['unit']})")
        a = r.analysis
        a = a[(a["resource"] == res) & (a["site_id"].isin(sel))]
        tbl = pd.DataFrame({
            "Site": a["site_id"],
            f"Baseline demand ({meta['unit']})": a["baseline_demand"],
            f"Month 0 demand, scenario ({meta['unit']})": a["month0_demand"],
            f"Month {H} demand ({meta['unit']})": a["horizon_demand"],
            f"Baseline capacity ({meta['unit']})": a["baseline_capacity"],
            f"Month {H} capacity ({meta['unit']})": a["horizon_capacity"],
            "Month 0 utilization (%)": a["month0_util_pct"],
            f"Month {H} utilization (%)": a["horizon_util_pct"],
            f"Month {H} headroom ({meta['unit']})": a["horizon_headroom"],
        })
        st.dataframe(tbl.round(2), hide_index=True, width="stretch")
        wa = fc[(fc["resource"] == res) & (fc["site_id"].isin(sel)) & (fc["month"].isin([0, H]))].groupby("month")[["demand", "capacity"]].sum()
        st.caption(f"Selected facilities combined: month {H} demand {wa.loc[H, 'demand']:,.1f} of {wa.loc[H, 'capacity']:,.1f} {meta['unit']} "
                   f"({100 * wa.loc[H, 'demand'] / wa.loc[H, 'capacity']:.1f}% weighted utilization).")

    with st.container(border=True):
        panel_title("Monthly Forecast Data")
        d = fc[(fc["resource"] == res) & (fc["site_id"].isin(sel)) & (fc["month"] <= H)].copy()
        d["status"] = d.apply(lambda x: "Over capacity" if x["exhausted"] else "Warning" if x["utilization_pct"] >= p.warn_pct else "OK", axis=1)
        out = d[["month", "site_id", "demand", "capacity", "utilization_pct", "headroom", "capacity_added", "status"]].rename(columns={
            "month": "Month", "site_id": "Site", "demand": f"Demand ({meta['unit']})", "capacity": f"Capacity ({meta['unit']})",
            "utilization_pct": "Utilization (%)", "headroom": f"Headroom ({meta['unit']})", "capacity_added": f"Expansion added ({meta['unit']})", "status": "Status"})
        st.dataframe(out.round(3), hide_index=True, width="stretch", height=320)
        chips([("Growth", "compound annual: demand x (1 + rate)^(month/12)"), ("Efficiency", f"{p.efficiency_pct:g}% demand reduction")])
