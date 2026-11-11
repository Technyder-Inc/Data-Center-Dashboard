"""Planned-expansion list shared by the sidebar and Scenario Planning."""
import streamlit as st

from components import state


def _resources(entries: list[dict]) -> str:
    power, cooling, racks = (sum(e[k] for e in entries) for k in ("power", "cooling", "racks"))
    parts = [f"+{power:g} MW" if power else "", f"+{cooling:g} MWe" if cooling else "", f"+{racks:g} racks" if racks else ""]
    return ", ".join(p for p in parts if p)


def expansion_list(container, prefix: str) -> None:
    """One block per facility. A facility with several activation months shows a combined total above its rows."""
    items = st.session_state["expansions"]
    if not items:
        return
    by_site: dict[str, list[tuple[int, dict]]] = {}
    for i, e in enumerate(items):
        by_site.setdefault(e["site"], []).append((i, e))
    for site in sorted(by_site):
        entries = sorted(by_site[site], key=lambda x: x[1]["month"])
        several = len(entries) > 1
        if several:
            container.caption(f"**{site} total (all months):** {_resources([e for _, e in entries])}")
        for i, e in entries:
            text, btn = container.columns([6, 1], vertical_alignment="center")
            text.caption(f"- from month {e['month']}: {_resources([e])}" if several else state.describe_expansion(e))
            btn.button("x", key=f"{prefix}_rm_{i}", on_click=state.remove_expansion, args=(i,), help="Remove this expansion")
    if len(items) > 1:
        container.button("Clear all expansions", key=f"{prefix}_clear", on_click=state.clear_expansions, width="stretch")
