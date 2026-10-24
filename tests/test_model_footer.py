"""The bottom of the Streamlit viewer should not have stacked model accordions."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
MODEL_PANEL = "Models & performance · methods, comparisons and results"
REFRESH_PANEL = "Refresh predictions · display or full cloud refresh"
MATCH_HISTORY_PANEL = "Historical Match Results · predictions vs final scores"


def _app(league):
    app = AppTest.from_file(str(ROOT / "viewer_dashboard.py"), default_timeout=60)
    app.run()
    assert not app.exception, f"Initial viewer load: {app.exception}"
    comp = next(c for c in app.selectbox if c.label == "Competition")
    comp.select(league).run()
    assert not app.exception, f"Selected {league}: {app.exception}"
    return app


def test_single_model_information_panel_and_separate_refresh_for_both_leagues():
    for league in ("EPL", "Championship"):
        app = _app(league)
        expanders = [item.label for item in app.get("expander")]
        assert expanders.count(MODEL_PANEL) == 1
        assert expanders.count(REFRESH_PANEL) == 1
        assert expanders.count(MATCH_HISTORY_PANEL) == 1
        assert len(expanders) == 3, f"Duplicate model accordions: {expanders}"
        tab_labels = [item.label for item in app.get("tab")]
        assert tab_labels == ["Models & formulas", "Match comparison", "Historical results"]


def test_whw_selection_preserves_single_footer_and_its_prediction_table():
    app = _app("Championship")
    selected = next(c for c in app.selectbox if c.label == "Prediction model")
    selected.select("W-H-W Analysis").run()
    assert not app.exception, f"W-H-W failed: {app.exception}"
    assert [item.label for item in app.get("expander")].count(MODEL_PANEL) == 1
    assert not any(x.label == "Underlying forecast" for x in app.selectbox)
    assert any({"Market", "Prediction", "Likelihood"}.issubset(df.value.columns)
               for df in app.dataframe)


def test_methodology_and_refresh_controls_are_kept():
    source = (ROOT / "viewer_dashboard.py").read_text(encoding="utf-8")
    assert "show_whw_formulas(embedded=True)" in source
    assert "whw_analysis.show_whw_history(metrics, embedded=True)" in source
    assert "show_league_accuracy(matrix_metrics, embedded=True)" in source
    assert "show_cloud_refresh(embedded=True)" in source
    assert "Refresh displayed predictions" in source


def test_old_model_accuracy_import_is_reloaded_on_app_run(monkeypatch):
    """Reproduce a cached pre-embedded helper from a long-lived Streamlit worker."""
    import model_accuracy

    def cached_old_helper(raw):
        raise TypeError("show_league_accuracy() got an unexpected keyword argument 'embedded'")

    monkeypatch.setattr(model_accuracy, "show_league_accuracy", cached_old_helper)
    app = _app("Championship")
    assert not app.exception
    assert [item.label for item in app.get("expander")].count(MODEL_PANEL) == 1


def test_cached_cloud_refresh_helper_updates_without_resetting_login_limits(monkeypatch):
    """Refresh cached UI definitions while retaining the authentication throttle."""
    import cloud_refresh_ui
    import streamlit as st

    def cached_old_cloud_refresh():
        with st.expander("Cloud Prediction Refresh"):
            st.caption("Legacy refresh controls")

    entries=cloud_refresh_ui._FAILED_ATTEMPTS
    lock=cloud_refresh_ui._AUTH_LOCK
    monkeypatch.setattr(cloud_refresh_ui, "show_cloud_refresh", cached_old_cloud_refresh)
    app = _app("EPL")
    assert not app.exception
    labels = [item.label for item in app.get("expander")]
    assert labels.count("Cloud Prediction Refresh") == 0
    assert cloud_refresh_ui._FAILED_ATTEMPTS is entries
    assert cloud_refresh_ui._AUTH_LOCK is lock
    assert labels.count(MODEL_PANEL) == 1
    source = (ROOT / "viewer_dashboard.py").read_text(encoding="utf-8")
    assert "importlib.reload(model_accuracy)" in source
