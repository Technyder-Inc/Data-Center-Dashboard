"""Exercise real Streamlit callbacks, reruns and cross-page state."""
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
    a.checkbox(key="ui_req_DC3").check()
    run(a)
    assert a.checkbox(key="ui_req_DC3").value
    a.number_input(key="cost_power").set_value(10.0)
    a.number_input(key="budget").set_value(50.0)
    run(a)
    assert not any(x.value for x in a.checkbox if x.key.startswith("ui_req_"))
    assert a.session_state["_result"].costs.power_per_mw_usd_m == 10
    page(a, "scenarios")
    assert a.number_input(key="budget").value == 50
    a.slider(key="warn_pct").set_value(99)
    run(a)
    assert a.session_state["_result"].params.critical_pct == 100
