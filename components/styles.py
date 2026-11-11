"""Dark navy executive styling. Lightweight CSS on top of Streamlit's dark theme."""
import streamlit as st

BLUE, GREEN, AMBER, RED = "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"
TEXT, MUTED, GRID = "#e6edff", "#9fb0d6", "rgba(148,163,184,0.16)"
RISK_TONE = {"Low": "green", "Medium": "amber", "High": "red", "Critical": "red"}

CSS = """
<style>
:root { --navy:#0a1128; --panel:#0f1b3d; --panel2:#13224c; --line:#1f3068; --text:#e6edff; --muted:#9fb0d6;
        --blue:#3b82f6; --green:#22c55e; --amber:#f59e0b; --red:#ef4444; }
.stApp { background: var(--navy); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding: 3.2rem 1.6rem 2rem 1.6rem; max-width: 100%; }
[data-testid="stSidebar"] { background:#0c1533; border-right:1px solid var(--line); min-width:290px; }
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
h1 { font-size: 2.1rem !important; font-weight: 700 !important; margin-bottom: .1rem; padding: 0; }
h2, h3 { font-weight: 650 !important; }
.page-sub { color: var(--muted); font-size: 1.02rem; margin: 0 0 1rem 0; }

.notice-bar { position: fixed; top: 0; left: 0; right: 0; z-index: 999990; height: 2.4rem; display:flex; align-items:center;
  justify-content:flex-end; gap:1.2rem; padding: 0 4.5rem 0 1rem; background:#0b1430; border-bottom:1px solid var(--line);
  color: var(--muted); font-size:.85rem; }
.notice-bar b { color: var(--text); font-weight:500; }

.brand { display:flex; align-items:center; gap:.7rem; font-size:1.2rem; font-weight:700; line-height:1.25; padding:.2rem 0 .8rem 0; }
.brand small { display:block; color: var(--muted); font-weight:500; font-size:.8rem; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] { border-radius:10px; padding:.55rem .8rem; color: var(--text); }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: var(--panel2); }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] { background: var(--blue); color:#fff; font-weight:600; }
.side-h { font-size:1.05rem; font-weight:650; margin:.9rem 0 .3rem 0; border-top:1px solid var(--line); padding-top:.9rem; }
.side-note { color: var(--muted); font-size:.8rem; line-height:1.35; }

[data-testid="stVerticalBlockBorderWrapper"] { background: var(--panel); border:1px solid var(--line) !important; border-radius:14px; }
.panel-title { font-size:1.12rem; font-weight:650; margin:0 0 .3rem 0; }

.kpi { background: var(--panel); border:1px solid var(--line); border-radius:14px; padding:.8rem 1rem; min-height:118px;
  border-left:4px solid var(--blue); height:100%; }
.kpi-green { border-left-color: var(--green); } .kpi-amber { border-left-color: var(--amber); } .kpi-red { border-left-color: var(--red); }
.kpi-label { color: var(--muted); font-size:.82rem; letter-spacing:.02em; }
.kpi-value { font-size:1.65rem; font-weight:700; line-height:1.25; margin:.15rem 0; }
.kpi-value.t-green { color:var(--green); } .kpi-value.t-amber { color:var(--amber); } .kpi-value.t-red { color:var(--red); } .kpi-value.t-blue { color:#7db3ff; }
.kpi-sub { color: var(--muted); font-size:.8rem; line-height:1.3; }

.tbl-wrap { overflow-x:auto; }
table.dc { width:100%; border-collapse:collapse; font-size:.88rem; }
table.dc th { text-align:left; color: var(--muted); font-weight:600; padding:.5rem .45rem; border-bottom:1px solid var(--line); }
table.dc td { padding:.5rem .45rem; border-bottom:1px solid rgba(31,48,104,.6); }
table.dc td.num, table.dc.nw td { white-space:nowrap; }
table.dc tr:last-child td { border-bottom:none; }
table.dc td.num, table.dc th.num { text-align:right; }
table.dc tr.hl td { background: rgba(239,68,68,.08); }
.pill { display:inline-block; padding:.1rem .6rem; border-radius:6px; font-size:.78rem; font-weight:650; color:#fff; }
.pill-green { background:#15803d; } .pill-amber { background:#b45309; } .pill-red { background:#b91c1c; } .pill-blue { background:#1d4ed8; } .pill-grey { background:#475569; }
.t-green { color: var(--green); } .t-amber { color: var(--amber); } .t-red { color: var(--red); }

.rec { display:flex; gap:.7rem; padding:.55rem 0; border-bottom:1px solid rgba(31,48,104,.6); }
.rec:last-child { border-bottom:none; }
.rec-n { flex:0 0 1.7rem; height:1.7rem; border-radius:50%; background:var(--blue); display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.85rem; }
.rec-n.sev-critical, .rec-n.sev-high { background:#b91c1c; } .rec-n.sev-medium { background:#b45309; } .rec-n.sev-info { background:#1d4ed8; }
.rec-t { font-weight:650; font-size:.92rem; } .rec-d { color: var(--muted); font-size:.84rem; line-height:1.35; }
ul.insights { margin:.2rem 0 .5rem 1.1rem; padding:0; } ul.insights li { margin:.25rem 0; font-size:.9rem; line-height:1.35; }
.assume { display:flex; flex-wrap:wrap; gap:.4rem; margin:.2rem 0 .6rem 0; }
.chip { background: var(--panel2); border:1px solid var(--line); border-radius:999px; padding:.15rem .7rem; font-size:.82rem; color: var(--text); }
.chip b { color:#7db3ff; font-weight:600; }

.stButton > button { border-radius:10px; border:1px solid var(--line); background:var(--panel2); color:var(--text); }
.stButton > button[kind="primary"] { background: var(--blue); border-color: var(--blue); color:#fff; }
.stButton > button:hover { border-color: var(--blue); }
[data-testid="stDownloadButton"] button { border-radius:10px; }
.ikpi { background: var(--panel); border:1px solid var(--line); border-radius:12px; padding:.7rem 1rem; display:flex; align-items:center; gap:.9rem; min-height:86px; height:100%; }
.ikpi svg { flex:0 0 34px; }
.ikpi-label { color: var(--text); font-size:.95rem; }
.ikpi-value { font-size:1.7rem; font-weight:700; line-height:1.2; }
.ikpi-value.amber { color: var(--amber); }
.panel-title.row { display:flex; align-items:center; gap:.5rem; }
.legend-lines { margin-top:.6rem; font-size:.95rem; line-height:1.9; }
.legend-lines i { display:inline-block; width:14px; height:14px; border-radius:3px; margin-right:.5rem; vertical-align:-2px; }
.rec-n.plain { background: transparent; border:2px solid var(--blue); color:#fff; }
@media (min-width:769px) {
  [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"], [data-testid="stSidebarResizeHandle"] { display:none !important; }
  section[data-testid="stSidebar"] { transform:none !important; margin-left:0 !important; visibility:visible !important; width:290px !important; min-width:290px !important; max-width:290px !important; }
}
@media (max-width:768px) {
  .notice-bar > span { display:none; }
  .notice-bar { left:3rem; right:3rem; font-size:.70rem; padding:0 .3rem; justify-content:center; pointer-events:none; }
}
.ikpi > div { min-width:0; }
.ikpi-value { font-size:clamp(1.1rem, 1.7vw, 1.7rem); overflow-wrap:anywhere; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def notice_bar() -> None:
    st.markdown(
        '<div class="notice-bar"><span>Data Center Operations Simulation</span>'
        "<span>|</span><b>Synthetic Data - Demonstration Only</b></div>",
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f"<h1>{title}</h1><div class='page-sub'>{subtitle}</div>", unsafe_allow_html=True)


def panel_title(text: str) -> None:
    st.markdown(f"<div class='panel-title'>{text}</div>", unsafe_allow_html=True)


def pill(text: str, tone: str) -> str:
    return f"<span class='pill pill-{tone}'>{text}</span>"


