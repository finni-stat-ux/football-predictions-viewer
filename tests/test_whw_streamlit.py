"""Regression test: W-H-W must render in the actual Streamlit viewer.

This exercises the same model selection path that failed on mobile.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_whw_render_for_both_leagues():
    root = Path(__file__).resolve().parents[1]
    for league in ("Championship", "EPL"):
        app = AppTest.from_file(str(root / "viewer_dashboard.py"), default_timeout=45)
        app.run()
        assert not app.exception, f"{league} initial load: {app.exception}"
        competition = next((x for x in app.selectbox if x.label == "Competition"), None)
        assert competition is not None
        if league not in competition.options:
            continue
        competition.set_value(league).run()
        assert not app.exception, f"{league} competition: {app.exception}"
        selector = next(x for x in app.selectbox if x.label == "Prediction model")
        selector.set_value("W-H-W Analysis").run()
        assert not app.exception, f"{league} W-H-W: {app.exception}"
        assert any("W-H-W" in str(x.value) for x in app.subheader)
