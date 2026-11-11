"""KPI cards, HTML tables and small formatting helpers shared by all pages."""
import pandas as pd
import streamlit as st

from components.styles import RISK_TONE, pill


def md(s: str) -> str:
    """Escape dollar signs so Streamlit markdown does not treat them as LaTeX."""
    return s.replace("$", "\\$")


def caption(s: str) -> None:
    st.caption(md(s))


def warning(s: str) -> None:
    st.warning(md(s))


def text(s: str) -> None:
    st.markdown(md(s))


def _h(s: str) -> str:
    return s.replace("$", "&#36;")


def month_text(m, none="None in horizon") -> str:
    return none if m is None or pd.isna(m) else f"Month {int(m)}"


UTIL_CAUTION_PCT = 70.0  # default; editable under Model Assumptions


def util_tone(pct: float, warn: float, exhausted: bool = False) -> str:
    """Display colour for a utilization value: green below 70%, amber up to the warning threshold, red from it."""
    if exhausted or pct >= warn:
        return "red"
    caution = getattr(st.session_state.get("assumptions"), "caution_pct", UTIL_CAUTION_PCT)
    return "amber" if pct >= caution else "green"


def util_cell(pct: float, warn: float) -> str:
    return f"<b class='t-{util_tone(pct, warn)}'>{pct:.1f}%</b>"


def risk_pill(level: str) -> str:
    return pill(level, RISK_TONE[level])


def html_table(headers: list[tuple[str, bool]], rows: list[list[str]], highlight: set[int] | None = None, nowrap: bool = False) -> None:
    """headers: (label, is_numeric). Cell values are trusted HTML produced by this app."""
    th = "".join(f"<th class='{'num' if num else ''}'>{h}</th>" for h, num in headers)
    body = ""
    for i, r in enumerate(rows):
        cls = " class='hl'" if highlight and i in highlight else ""
        tds = "".join(f"<td class='{'num' if headers[j][1] else ''}'>{c}</td>" for j, c in enumerate(r))
        body += f"<tr{cls}>{tds}</tr>"
    st.markdown(_h(f"<div class='tbl-wrap'><table class='dc{" nw" if nowrap else ""}'><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>"), unsafe_allow_html=True)


def chips(items: list[tuple[str, str]]) -> None:
    html = "".join(f"<span class='chip'>{k}: <b>{v}</b></span>" for k, v in items)
    st.markdown(_h(f"<div class='assume'>{html}</div>"), unsafe_allow_html=True)


def recommendations_list(recs: list[dict]) -> None:
    html = "".join(
        f"<div class='rec'><div class='rec-n sev-{r['severity']}'>{r['priority']}</div>"
        f"<div><div class='rec-t'>{r['title']}</div><div class='rec-d'>{r['detail']}</div></div></div>"
        for r in recs
    )
    st.markdown(_h(html), unsafe_allow_html=True)


def bullet_list(items: list[str]) -> None:
    st.markdown(_h("<ul class='insights'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"), unsafe_allow_html=True)


ICONS = {
    "server": "<rect x='3' y='3.5' width='18' height='5' rx='1.3' fill='#2f7de1' stroke='none'/><rect x='3' y='9.5' width='18' height='5' rx='1.3' fill='#2f7de1' stroke='none'/><rect x='3' y='15.5' width='18' height='5' rx='1.3' fill='#2f7de1' stroke='none'/><circle cx='6.5' cy='6' r='.9' fill='#0f1b3d' stroke='none'/><circle cx='6.5' cy='12' r='.9' fill='#0f1b3d' stroke='none'/><circle cx='6.5' cy='18' r='.9' fill='#0f1b3d' stroke='none'/>",
    "bolt": "<path d='M13 2 5 13h6l-1 9 8-11h-6z' fill='#f6b400' stroke='#f6b400'/>",
    "layers": "<path d='m12 2.5 9 4.5-9 4.5-9-4.5z'/><path d='m3 11.5 9 4.5 9-4.5'/><path d='m3 16 9 4.5 9-4.5'/>",
    "trend": "<path d='M3 17 9 11l4 4 8-8'/><path d='M15 7h6v6'/>",
    "calendar": "<rect x='3' y='5' width='18' height='16' rx='2'/><path d='M3 10h18M8 3v4M16 3v4'/>",
    "coins": "<ellipse cx='12' cy='6' rx='7' ry='3'/><path d='M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6'/><path d='M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6'/>",
}


def icon_kpi(icon: str, label: str, value: str, color: str = "#3b82f6", amber: bool = False, sub: str = "", tone: str = "", tall: bool = False) -> str:
    stroke = "#22c55e" if icon == "layers" else "#f59e0b" if icon in ("calendar", "coins") else color
    svg = f"<svg width='34' height='34' viewBox='0 0 24 24' fill='none' stroke='{stroke}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>{ICONS[icon]}</svg>"
    vcls = " amber" if amber else f" t-{tone}" if tone else ""
    subhtml = f"<div class='ikpi-sub'>{sub}</div>" if sub else ""
    return _h(f"<div class='ikpi{' has-sub' if sub or tall else ''}'>{svg}<div><div class='ikpi-label'>{label}</div><div class='ikpi-value{vcls}'>{value}</div>{subhtml}</div></div>")


def simple_recs(items: list[str]) -> None:
    html = "".join(f"<div class='rec'><div class='rec-n plain'>{i}</div><div class='rec-t' style='font-weight:500;font-size:1rem'>{t}</div></div>" for i, t in enumerate(items, 1))
    st.markdown(_h(html), unsafe_allow_html=True)
