"""Exercise real Streamlit callbacks, reruns and cross-page state."""
import math
from pathlib import Path
from types import SimpleNamespace

from streamlit.navigation.page import StreamlitPage
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def run(app):
    # Streamlit 1.49's AppTest assumes all ButtonGroups are multi-select.
    # Wrap the scalar solely for widget-state serialization; the app receives a scalar.
    for group in app.get("button_group"):
        if isinstance(group.value, str):
            group.set_value([group.value])
    app.run()
    assert not app.exception
    assert not any("was created with a default value" in w.value for w in app.warning)
    return app


def page(app, url):
    # AppTest.switch_page only supports file pages; this app registers callable pages.
    app._page_hash = StreamlitPage._script_hash.fget(SimpleNamespace(_url_path=url))
    return run(app)


def test_all_pages_presets_reset_and_persistence():
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not a.exception
    assert a.session_state["_result"].portfolio["power_month0_demand"] == 32.5
    page(a, "scenarios")
    for name in ("High Growth", "Infrastructure Expansion", "Efficiency Optimization", "Budget-Constrained", "Baseline"):
        a.button(key=f"sp_{name}").click()
        run(a)
        p = a.session_state["_result"].params
        assert p.name == name
        assert p.efficiency_pct == (10 if name == "Efficiency Optimization" else 0)
        assert p.fund_planned_projects == (name == "Budget-Constrained")
    a.number_input(key="exp_cooling").set_value(4.0)
    a.number_input(key="exp_month").set_value(8)
    a.button(key="pg_add_exp").click()
    run(a)
    a.multiselect(key="override_sites").set_value(["DC2"])
    run(a)
    a.number_input(key="sg_DC2").set_value(30.0)
    run(a)
    r = a.session_state["_result"]
    assert r.params.site_growth_overrides == {"DC2": 30}
    assert r.params.expansions[0].cooling_mwe == 4
    for url in ("forecasting", "decisions", "", "scenarios"):
        page(a, url)
        assert a.session_state["_result"].portfolio == r.portfolio
    page(a, "forecasting")
    a.get("button_group")[0].set_value(["Cooling"])
    run(a)
    a.multiselect(key="ui_fc_sites").set_value(["DC3"])
    run(a)
    assert a.radio(key="ui_fc_view_False").value == "Demand vs capacity"
    page(a, "scenarios")
    a.button(key="sp_reset").click()
    run(a)
    p = a.session_state["_result"].params
    assert not p.expansions and not p.site_growth_overrides and p.growth_mode == "site"
    assert p.horizon == 36 and p.budget_usd_m == 100


def test_sidebar_slider_costs_budget_and_thresholds():
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    a.slider(key="growth_override").set_value(20.0)
    run(a)
    assert a.session_state["_result"].portfolio["power_demand_month12"] == 39
    page(a, "decisions")
    a.number_input(key="cost_power").set_value(10.0)
    a.number_input(key="budget").set_value(50.0)
    run(a)
    assert a.session_state["_result"].costs.power_per_mw_usd_m == 10
    page(a, "scenarios")
    assert a.number_input(key="budget").value == 50
    a.slider(key="warn_pct").set_value(99)
    run(a)
    assert a.session_state["_result"].params.critical_pct == 100


def test_sidebar_keeps_multiple_expansions():
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    a.selectbox(key="ui_exp_choice").set_value("Add Cooling (MWe)")
    run(a)
    a.selectbox(key="sb_exp_site").set_value("DC3")
    a.number_input(key="sb_amt_exp_cooling").set_value(4.0)
    a.button(key="sb_add_exp").click()
    run(a)
    a.selectbox(key="ui_exp_choice").set_value("Add Power (MW)")
    run(a)
    a.selectbox(key="sb_exp_site").set_value("DC4")
    a.number_input(key="sb_amt_exp_power").set_value(2.0)
    a.button(key="sb_add_exp").click()
    run(a)
    ex = a.session_state["_result"].params.expansions
    assert [(e.site_id, e.cooling_mwe, e.power_mw) for e in ex] == [("DC3", 4.0, 0.0), ("DC4", 0.0, 2.0)]
    a.button(key="sb_rm_0").click()
    run(a)
    ex = a.session_state["_result"].params.expansions
    assert [(e.site_id, e.power_mw) for e in ex] == [("DC4", 2.0)]


def test_same_facility_and_month_adds_up_but_other_months_stay_separate():
    a = AppTest.from_file(str(APP), default_timeout=30).run()

    def add(resource, site, amount, month):
        a.selectbox(key="ui_exp_choice").set_value(resource)
        run(a)
        key = {"Add Power (MW)": "sb_amt_exp_power", "Add Cooling (MWe)": "sb_amt_exp_cooling"}[resource]
        a.selectbox(key="sb_exp_site").set_value(site)
        a.number_input(key=key).set_value(amount)
        a.number_input(key="sb_exp_month").set_value(month)
        a.button(key="sb_add_exp").click()
        run(a)

    add("Add Power (MW)", "DC3", 1.0, 0)
    add("Add Power (MW)", "DC3", 2.0, 0)
    ex = a.session_state["_result"].params.expansions
    assert [(e.site_id, e.power_mw, e.month) for e in ex] == [("DC3", 3.0, 0)]
    add("Add Cooling (MWe)", "DC3", 4.0, 0)
    ex = a.session_state["_result"].params.expansions
    assert [(e.site_id, e.power_mw, e.cooling_mwe) for e in ex] == [("DC3", 3.0, 4.0)]
    add("Add Power (MW)", "DC3", 1.0, 12)
    ex = a.session_state["_result"].params.expansions
    assert [(e.site_id, e.power_mw, e.month) for e in ex] == [("DC3", 3.0, 0), ("DC3", 1.0, 12)]
    assert any("DC3 total" in c.value for c in a.sidebar.caption)


def test_edited_data_and_assumptions_flow_through_the_app(sites=None):
    from dataclasses import replace
    from models.assumptions import DEFAULT_ASSUMPTIONS
    from models.editing import EDITABLE_COLUMNS, apply_site_edits
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    original = a.session_state["_result"].sites
    frame = original[["site_id", *EDITABLE_COLUMNS]].copy()
    frame.loc[2, "cooling_capacity_mwe"] = 14.0
    df, errors, _ = apply_site_edits(original, frame)
    assert not errors
    a.session_state["sites_override"] = df
    a.session_state["assumptions"] = replace(DEFAULT_ASSUMPTIONS, high_growth_pct=30.0)
    run(a)
    r = a.session_state["_result"]
    assert r.sites.loc[2, "cooling_capacity_mwe"] == 14.0 and round(r.portfolio["cooling_baseline_capacity"], 6) == round(42.4 - 9.2 + 14.0, 6)
    assert any(b.label == "High Growth (30%)" for b in a.sidebar.button)
    a.button(key="side_High Growth").click()
    run(a)
    assert a.session_state["_result"].params.growth_value_pct == 30.0
    page(a, "forecasting")
    assert not a.exception and any("Edited in this session" in c.value for c in a.caption)


WIDGET_LIMITS = {
    "growth_override": "portfolio_growth_pct", "ui_sp_growth": "portfolio_growth_pct", "growth_adjust": "growth_adjust_pts", "efficiency": "efficiency_pct",
    "budget": "budget_usd_m", "warn_pct": "warn_pct", "crit_pct": "critical_pct", "exp_power": "expansion_power_mw", "exp_cooling": "expansion_cooling_mwe",
    "exp_racks": "expansion_racks", "exp_month": "month", "cost_power": "cost_per_mw", "cost_cooling": "cost_per_mwe", "cost_rack": "cost_per_rack",
    "sb_exp_month": "month", "sb_amt_exp_power": "expansion_power_mw", "sb_amt_exp_cooling": "expansion_cooling_mwe", "sb_amt_exp_racks": "expansion_racks",
}


def run_without_asserts(app):
    for group in app.get("button_group"):
        if isinstance(group.value, str):
            group.set_value([group.value])
    app.run()


def test_every_numeric_widget_is_bounded_by_the_shared_limits():
    from utils.validation import LIMITS
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    seen = set()
    for resource in ("Add Power (MW)", "Add Cooling (MWe)", "Add Racks"):
        a.selectbox(key="ui_exp_choice").set_value(resource)
        run(a)
        for url in ("", "scenarios", "decisions", "forecasting"):
            page(a, url)
            for w in [*a.number_input, *a.slider]:
                assert w.min is not None and w.max is not None, w.key
                assert math.isfinite(w.min) and math.isfinite(w.max), w.key
                key = w.key or ""
                limit = WIDGET_LIMITS.get(key) or ("growth_pct" if key.startswith("sg_") else None)
                if limit:
                    assert (w.min, w.max) == LIMITS[limit], (key, w.min, w.max, LIMITS[limit])
                    seen.add(key)
    assert {"growth_override", "budget", "efficiency", "exp_power", "exp_racks", "cost_rack", "warn_pct", "sb_amt_exp_racks"} <= seen


def test_bad_stored_values_are_reset_instead_of_crashing():
    cases = {"budget": [-5.0, 5000.0, float("nan"), float("inf"), None], "efficiency": [99.0, -1.0, float("nan")],
             "exp_power": [500.0, -3.0, None], "exp_racks": [99999, -1], "exp_month": [99, -2], "growth_override": [500.0, float("nan")],
             "cost_power": [1e9, -1.0], "warn_pct": [1, 200], "sg_DC2": [1000.0, float("nan")]}
    for key, values in cases.items():
        for bad in values:
            a = AppTest.from_file(str(APP), default_timeout=30).run()
            page(a, "scenarios")
            a.session_state[key] = bad
            run_without_asserts(a)
            assert not a.exception, (key, bad, [e.value[:80] for e in a.exception])
            assert not a.error, (key, bad)
            if bad is not None:  # None means "no value": Streamlit falls back to the widget default, nothing to reset
                assert any("were reset to defaults" in w.value and key in w.value for w in a.warning), (key, bad)
            assert 0 <= a.session_state["_result"].params.budget_usd_m <= 1000
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    a.session_state["expansions"] = [{"site": "DC9", "power": 1.0, "cooling": 0.0, "racks": 0, "month": 0},
                                     {"site": "DC1", "power": 1000.0, "cooling": 0.0, "racks": 0, "month": 0},
                                     {"site": "DC1", "power": 1.0, "cooling": 0.0, "racks": 0, "month": 5}]
    run_without_asserts(a)
    assert not a.exception and [(e.site_id, e.month) for e in a.session_state["_result"].params.expansions] == [("DC1", 5)]
