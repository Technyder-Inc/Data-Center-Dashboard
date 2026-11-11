"""Dark navy executive styling. Lightweight CSS on top of Streamlit's dark theme."""
import streamlit as st

BLUE, GREEN, AMBER, RED = "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"
TEXT, MUTED, GRID = "#e6edff", "#9fb0d6", "rgba(148,163,184,0.16)"
RISK_TONE = {"Low": "green", "Medium": "amber", "High": "red", "Critical": "crimson"}

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

.brand { display:flex; align-items:center; gap:.7rem; font-size:1.2rem; font-weight:700; line-height:1.25; padding:.2rem 0 1.4rem 0; }
[class*="st-key-nav_"] { margin-bottom:.85rem; }
.st-key-nav_0 { margin-top:1.5rem; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] { border-radius:10px; padding:.55rem .8rem; color: var(--text); }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: var(--panel2); }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.45rem; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background:#0e1a3e; border:1px solid #2d4488; }
[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] { display:none; }
.slider-label { display:flex; justify-content:space-between; font-size:.9rem; margin:.5rem 0 -.3rem 0; }
.panel-title svg { vertical-align:-4px; margin-right:.5rem; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] { background: var(--blue); color:#fff; font-weight:600; }
.side-h { font-size:1.05rem; font-weight:650; margin:.9rem 0 .55rem 0; border-top:1px solid var(--line); padding-top:.9rem; }

[data-testid="stVerticalBlockBorderWrapper"] { background: var(--panel); border:1px solid var(--line) !important; border-radius:14px; }
.panel-title { font-size:1.12rem; font-weight:650; margin:0 0 .3rem 0; }


.tbl-wrap { overflow-x:auto; }
table.dc { width:100%; border-collapse:collapse; font-size:.95rem; }
table.dc th { text-align:left; color:#fff; font-weight:600; padding:.55rem .5rem; border-bottom:1px solid var(--line); line-height:1.25; }
table.dc td { padding:.6rem .5rem; border-bottom:1px solid rgba(31,48,104,.6); }
table.dc td.num, table.dc.nw td { white-space:nowrap; }
table.dc tr:last-child td { border-bottom:none; }
table.dc td.num, table.dc th.num { text-align:center; }
table.dc tr.hl td { background: rgba(239,68,68,.08); }
table.dc b[class^='t-'] { font-size:1.02rem; }
.pill { display:inline-block; min-width:74px; text-align:center; padding:.22rem .7rem; border-radius:7px; font-size:.85rem; font-weight:600; color:#fff; }
.pill-green { background:#17712f; color:#c9f7d4; } .pill-amber { background:#f5b50b; color:#1c1500; } .pill-red { background:#d9303d; } .pill-crimson { background:#9f1239; }
.pill-blue { background:#1d4ed8; } .pill-grey { background:#475569; }
.t-green { color:#4ade80; } .t-amber { color:#fbb024; } .t-red { color:#f43f5e; }

.rec { display:flex; gap:.7rem; padding:.55rem 0; border-bottom:1px solid rgba(31,48,104,.6); }
.rec:last-child { border-bottom:none; }
.rec-n { flex:0 0 2rem; height:2rem; border-radius:50%; background:var(--blue); display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.85rem; }
.rec-n.sev-critical, .rec-n.sev-high { background:#b91c1c; } .rec-n.sev-medium { background:#b45309; } .rec-n.sev-info { background:#1d4ed8; }
.rec-t { font-weight:650; font-size:.92rem; } .rec-d { color: var(--muted); font-size:.84rem; line-height:1.35; }
ul.insights { margin:.2rem 0 .5rem 1.1rem; padding:0; } ul.insights li { margin:.25rem 0; font-size:.95rem; line-height:1.35; }
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
.ikpi-value.amber { color: var(--amber); } .ikpi-value.t-red { color:#f43f5e; } .ikpi-value.t-green { color:#4ade80; }
.ikpi.has-sub { min-height:122px; }
.ikpi-sub { color: var(--muted); font-size:.78rem; line-height:1.25; }
.legend-lines { margin-top:.6rem; font-size:.95rem; line-height:1.9; }
.legend-lines i { display:inline-block; width:14px; height:14px; border-radius:3px; margin-right:.5rem; vertical-align:-2px; }
.rec-n.plain { background:#1e78e6; color:#fff; }
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

/* Responsive layout: columns wrap instead of squeezing, tables scroll, sidebar narrows on tablets */
[data-testid="stMain"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap; row-gap:.8rem; }
[data-testid="stMain"] [data-testid="stColumn"] { min-width:340px; }
[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.ikpi) > [data-testid="stColumn"] { min-width:210px; }
[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.legend-lines) > [data-testid="stColumn"] { min-width:150px; }
[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has([data-testid="stSegmentedControl"]) > [data-testid="stColumn"] { min-width:200px; }
.tbl-wrap { max-width:100%; }
[data-testid="stNumberInputContainer"]:has(input:invalid) { outline:2px solid #f43f5e; border-radius:8px; }
[data-testid="stNumberInputContainer"]:has(input:invalid) input { color:#f43f5e !important; }
[data-testid="stNumberInput"]:has(input:invalid)::after { content:"Outside the allowed range: this value is not applied"; display:block; color:#f43f5e; font-size:.75rem; padding:.25rem .1rem 0 .1rem; }
[class*="_rm_"] button { min-height:1.7rem; padding:0 .4rem; font-size:.8rem; }
@media (max-width:1100px) and (min-width:769px) {
  section[data-testid="stSidebar"] { width:250px !important; min-width:250px !important; max-width:250px !important; }
  .block-container { padding-left:1.1rem; padding-right:1.1rem; }
  h1 { font-size:1.8rem !important; }
}
@media (max-width:768px) {
  .block-container { padding:3.2rem .8rem 1.5rem 2.8rem; }
  h1 { font-size:1.5rem !important; }
  .page-sub { font-size:.9rem; }
  .panel-title { font-size:1rem; }
  .ikpi { min-height:72px; padding:.55rem .8rem; }
  .ikpi-value { font-size:1.35rem; }
  table.dc { font-size:.85rem; }
  .assume { gap:.3rem; }
  .chip { font-size:.75rem; }
  [data-testid="stMain"] [data-testid="stColumn"] { min-width:100%; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.ikpi) > [data-testid="stColumn"] { min-width:100%; }
}
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


TITLE_ICONS = {
    "info": "<circle cx='12' cy='12' r='9'/><path d='M12 11v6M12 7.5v.5'/>",
    "target": "<circle cx='12' cy='12' r='9'/><circle cx='12' cy='12' r='5'/><circle cx='12' cy='12' r='1.2'/><path d='m13 11 7-7'/>",
}


def panel_title(text: str, icon: str | None = None) -> None:
    svg = (f"<svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#7db3ff' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>{TITLE_ICONS[icon]}</svg>" if icon else "")
    st.markdown(f"<div class='panel-title'>{svg}{text}</div>", unsafe_allow_html=True)


def pill(text: str, tone: str) -> str:
    return f"<span class='pill pill-{tone}'>{text}</span>"


