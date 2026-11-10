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


def kpi_card(label: str, value: str, sub: str = "", tone: str = "blue") -> str:
    return _h(
        f"<div class='kpi kpi-{tone}'><div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value t-{tone}'>{value}</div><div class='kpi-sub'>{sub}</div></div>"
    )


def kpi_row(cards: list[str]) -> None:
    for col, html in zip(st.columns(len(cards)), cards):
        col.markdown(html, unsafe_allow_html=True)


def month_text(m, none="None in horizon") -> str:
    return none if m is None or pd.isna(m) else f"Month {int(m)}"


def util_tone(pct: float, warn: float, crit: float, exhausted: bool = False) -> str:
    if exhausted or pct > 100 + 1e-9:
        return "red"
    return "red" if pct >= crit else "amber" if pct >= warn else "green"


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
    "server": "<rect x='3' y='4' width='18' height='4' rx='1'/><rect x='3' y='10' width='18' height='4' rx='1'/><rect x='3' y='16' width='18' height='4' rx='1'/>",
    "bolt": "<path d='M13 2 5 13h6l-1 9 8-11h-6z' fill='#f59e0b'/>",
    "layers": "<path d='m12 3 9 5-9 5-9-5z'/><path d='m3 13 9 5 9-5'/>",
    "trend": "<path d='M3 17 9 11l4 4 8-8'/><path d='M15 7h6v6'/>",
    "calendar": "<rect x='3' y='5' width='18' height='16' rx='2'/><path d='M3 10h18M8 3v4M16 3v4'/>",
}


def icon_kpi(icon: str, label: str, value: str, color: str = "#3b82f6", amber: bool = False) -> str:
    stroke = "#22c55e" if icon == "layers" else "#f59e0b" if icon == "calendar" else color
    svg = f"<svg width='34' height='34' viewBox='0 0 24 24' fill='none' stroke='{stroke}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>{ICONS[icon]}</svg>"
    return f"<div class='ikpi'>{svg}<div><div class='ikpi-label'>{label}</div><div class='ikpi-value{' amber' if amber else ''}'>{value}</div></div></div>"


def simple_recs(items: list[str]) -> None:
    html = "".join(f"<div class='rec'><div class='rec-n plain'>{i}</div><div class='rec-t' style='font-weight:500'>{t}</div></div>" for i, t in enumerate(items, 1))
    st.markdown(_h(html), unsafe_allow_html=True)
