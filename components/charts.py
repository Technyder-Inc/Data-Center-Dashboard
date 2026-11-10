"""Plotly figures with a consistent dark executive style."""
import pandas as pd
import plotly.graph_objects as go

from components.styles import AMBER, BLUE, GREEN, GRID, MUTED, RED, TEXT
from models.forecast import RESOURCE_META

SITE_COLORS = ["#60a5fa", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#fb923c"]


def _layout(fig: go.Figure, height: int, ytitle: str, horizon: int, top: int = 70) -> go.Figure:
    ticks = list(range(0, horizon + 1, 6))
    fig.update_layout(
        height=height,
        margin=dict(l=60, r=24, t=top, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0, font=dict(size=11)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#13224c", font_color=TEXT),
        xaxis=dict(title="Forecast month", tickmode="array", tickvals=ticks, ticktext=["Now" if t == 0 else f"{t}M" for t in ticks],
                   gridcolor=GRID, zeroline=False, range=[0, horizon], automargin=True),
        yaxis=dict(title=ytitle, gridcolor=GRID, zeroline=False, automargin=True),
    )
    return fig


def portfolio_forecast(ps: pd.DataFrame, pf: dict, params, expansions: list) -> go.Figure:
    d = ps[(ps["resource"] == "power") & (ps["month"] <= params.horizon)].sort_values("month")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["month"], y=d["demand"], name="Demand (MW)", mode="lines", line=dict(color=BLUE, width=3),
                             fill="tozeroy", fillcolor="rgba(59,130,246,0.14)", hovertemplate="Month %{x}: %{y:,.2f} MW<extra>Demand</extra>"))
    six = d[d["month"] % 6 == 0]
    fig.add_trace(go.Scatter(x=six["month"], y=six["demand"], mode="markers", marker=dict(color=BLUE, size=8), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=d["month"], y=d["capacity"], name="Capacity (MW)", mode="lines",
                             line=dict(color=GREEN, width=2.5, dash="dash", shape="hv"), hovertemplate="Month %{x}: %{y:,.2f} MW<extra>Capacity</extra>"))
    lo, hi = min(d["demand"].min(), d["capacity"].min()), max(d["demand"].max(), d["capacity"].max())
    fig.update_yaxes(range=[max(0, lo * 0.8), hi * 1.1])
    _layout(fig, 400, "Power (MW)", params.horizon, top=60)
    fig.update_xaxes(title="")
    agg = pf["aggregate_exhaustion_by_resource"]["power"]
    if agg is not None:
        y = float(d[d["month"] == agg]["demand"].iloc[0])
        fig.add_trace(go.Scatter(x=[agg], y=[y], mode="markers", marker=dict(color=AMBER, size=10), showlegend=False, hoverinfo="skip"))
        fig.add_annotation(x=agg, y=y, text=f"<b>Portfolio Capacity Exhausted</b><br>~ {agg} Months", showarrow=True, arrowhead=2, arrowcolor=AMBER,
                           ax=-40, ay=-70, bgcolor="#2a1f08", bordercolor=AMBER, borderwidth=1.5, font=dict(color="#fbbf24", size=12))
    return fig


def utilization_donut(used: float, cap: float, unit: str) -> go.Figure:
    avail = max(cap - used, 0.0)
    pct = 100 * used / cap
    fig = go.Figure(go.Pie(labels=["Used", "Available"], values=[used, avail], hole=0.62, sort=False, direction="clockwise", showlegend=False,
                           marker=dict(colors=[GREEN, BLUE], line=dict(color="#0f1b3d", width=2)), textinfo="none",
                           hovertemplate="%{label}: %{value:,.1f} " + unit + " (%{percent})<extra></extra>"))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT),
                      annotations=[dict(text=f"<b>{pct:.1f}%</b><br>Utilized", showarrow=False, font=dict(size=20))])
    return fig


def site_forecast(fc: pd.DataFrame, site_ids: list[str], resource: str, view: str, params, expansions: list, all_ids: list[str]) -> go.Figure:
    meta = RESOURCE_META[resource]
    unit = meta["unit"]
    fig = go.Figure()
    d_all = fc[(fc["resource"] == resource) & (fc["month"] <= params.horizon)]
    for sid in site_ids:
        color = SITE_COLORS[all_ids.index(sid) % len(SITE_COLORS)]
        d = d_all[d_all["site_id"] == sid].sort_values("month")
        if view == "Utilization (%)":
            fig.add_trace(go.Scatter(x=d["month"], y=d["utilization_pct"], name=sid, mode="lines", line=dict(color=color, width=2.5),
                                     hovertemplate=f"{sid} month " + "%{x}: %{y:.1f}%<extra></extra>"))
            ex = d[d["exhausted"]].head(1)
            if len(ex):
                fig.add_trace(go.Scatter(x=ex["month"], y=ex["utilization_pct"], mode="markers", showlegend=False,
                                         marker=dict(symbol="x", color=RED, size=12, line=dict(width=2, color=RED)),
                                         hovertemplate=f"{sid} exhausted in month " + "%{x}<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(x=d["month"], y=d["demand"], name=f"{sid} demand", mode="lines", line=dict(color=color, width=2.5),
                                     hovertemplate=f"{sid} demand month " + "%{x}: %{y:,.2f} " + unit + "<extra></extra>"))
            fig.add_trace(go.Scatter(x=d["month"], y=d["capacity"], name=f"{sid} capacity", mode="lines",
                                     line=dict(color=color, width=1.8, dash="dash", shape="hv"),
                                     hovertemplate=f"{sid} capacity month " + "%{x}: %{y:,.2f} " + unit + "<extra></extra>"))
            ex = d[d["exhausted"]].head(1)
            if len(ex):
                fig.add_trace(go.Scatter(x=ex["month"], y=ex["demand"], mode="markers", showlegend=False,
                                         marker=dict(symbol="x", color=RED, size=12, line=dict(width=2, color=RED)),
                                         hovertemplate=f"{sid} exhausted in month " + "%{x}<extra></extra>"))
        for e in expansions:
            if e.site_id == sid and getattr(e, meta["exp"]) > 0 and e.month <= params.horizon:
                yv = d[d["month"] == e.month]["utilization_pct" if view == "Utilization (%)" else "capacity"].iloc[0]
                fig.add_trace(go.Scatter(x=[e.month], y=[yv], mode="markers", showlegend=False,
                                         marker=dict(symbol="diamond", size=11, color="#7dd3fc", line=dict(width=1, color="#0a1128")),
                                         hovertemplate=f"{sid} expansion active month {e.month}<extra></extra>"))
    if view == "Utilization (%)":
        fig.add_hline(y=100, line=dict(color=RED, dash="dash", width=1.3))
        fig.add_hline(y=params.warn_pct, line=dict(color=AMBER, dash="dot", width=1.3))
        fig.add_hline(y=params.critical_pct, line=dict(color="#fb7185", dash="dot", width=1))
        ytitle = f"{meta['label']} utilization (%)"
    else:
        ytitle = f"{meta['label']} ({unit})"
    _layout(fig, 430, ytitle, params.horizon, top=60)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
    return fig


def before_after(ps_base: pd.DataFrame, ps_scn: pd.DataFrame, resource: str, params) -> go.Figure:
    meta = RESOURCE_META[resource]
    fig = go.Figure()
    for ps, name, color, dash in ((ps_base, "Baseline", MUTED, "dash"), (ps_scn, "Scenario", BLUE, "solid")):
        d = ps[(ps["resource"] == resource) & (ps["month"] <= params.horizon)].sort_values("month")
        fig.add_trace(go.Scatter(x=d["month"], y=d["utilization_pct"], name=f"{name} utilization", mode="lines",
                                 line=dict(color=color, width=3 if name == "Scenario" else 2, dash=dash),
                                 hovertemplate=f"{name} month " + "%{x}: %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=100, line=dict(color=RED, dash="dash", width=1.3))
    fig.add_hline(y=params.warn_pct, line=dict(color=AMBER, dash="dot", width=1.3))
    return _layout(fig, 340, f"Portfolio {meta['label'].lower()} utilization (%)", params.horizon, top=60)


def peak_comparison(ss_base: pd.DataFrame, ss_scn: pd.DataFrame, params) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ss_base["site_id"], y=ss_base["peak_util_pct"], name="Baseline peak", marker_color="#64748b",
                         hovertemplate="%{x} baseline peak: %{y:.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(x=ss_scn["site_id"], y=ss_scn["peak_util_pct"], name="Scenario peak", marker_color=BLUE,
                         hovertemplate="%{x} scenario peak: %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=100, line=dict(color=RED, dash="dash", width=1.3))
    fig.add_hline(y=params.warn_pct, line=dict(color=AMBER, dash="dot", width=1.3))
    fig.update_layout(barmode="group", height=340, margin=dict(l=60, r=24, t=60, b=50), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT), hovermode="closest",
                      legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
                      yaxis=dict(title="Peak utilization within horizon (%)", gridcolor=GRID, automargin=True),
                      xaxis=dict(automargin=True))
    return fig


def project_costs(projects: pd.DataFrame, available: float) -> go.Figure:
    colors = [GREEN if s == "Funded" else "#64748b" for s in projects["funding_status"]]
    fig = go.Figure(go.Bar(x=projects["site_id"], y=projects["cost_usd_m"], marker_color=colors,
                           text=[f"${c:.1f}M" for c in projects["cost_usd_m"]], textposition="outside", cliponaxis=False,
                           customdata=projects[["priority_rank", "funding_status"]],
                           hovertemplate="%{x} (rank %{customdata[0]}): $%{y:.1f}M, %{customdata[1]}<extra></extra>"))
    fig.add_hline(y=available, line=dict(color=AMBER, dash="dash", width=1.5),
                  annotation_text=f"Budget available for planned projects: ${available:.1f}M", annotation_position="top left",
                  annotation_font_color="#fde68a")
    fig.update_layout(height=320, margin=dict(l=60, r=24, t=50, b=50), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TEXT), hovermode="closest",
                      yaxis=dict(title="Project cost (USD millions)", gridcolor=GRID, automargin=True,
                                 range=[0, max(projects["cost_usd_m"].max(), available) * 1.25]),
                      xaxis=dict(title="Projects in priority order", categoryorder="array", categoryarray=list(projects["site_id"]), automargin=True))
    return fig
