"""Prevent expired football snapshots from hiding their own recovery controls."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree():
    return ast.parse((ROOT / "viewer_dashboard.py").read_text(encoding="utf-8"))


def _top_level_if(tree, condition):
    matching = [
        node for node in tree.body
        if isinstance(node, ast.If) and ast.unparse(node.test) == condition
    ]
    assert len(matching) == 1, f"Expected one top-level {condition!r} branch"
    return matching[0]


def _calls(node):
    return [
        ast.unparse(item.func) for statement in node.body
        for item in ast.walk(statement) if isinstance(item, ast.Call)
    ]


def _verify_refresh_before_stop(branch):
    calls = _calls(branch)
    assert "render_refresh_controls" in calls
    assert "st.stop" in calls
    assert calls.index("render_refresh_controls") < calls.index("st.stop")


def test_empty_prediction_snapshot_still_shows_refresh():
    tree = _tree()
    defs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "render_refresh_controls"
    ]
    assert len(defs) == 1
    branch = _top_level_if(tree, "predictions.empty")
    assert defs[0].lineno < branch.lineno
    _verify_refresh_before_stop(branch)


def test_expired_fixtures_still_show_refresh_and_archived_results():
    branch = _top_level_if(_tree(), "options.empty")
    _verify_refresh_before_stop(branch)
    calls = _calls(branch)
    assert "historical_matches.show_historical_matches" in calls
    assert calls.index("historical_matches.show_historical_matches") < calls.index("st.stop")


def test_normal_fixture_screen_has_exactly_one_refresh_panel():
    tree = _tree()
    normal_calls = [
        ast.unparse(node.value.func) for node in tree.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    ]
    assert normal_calls.count("render_refresh_controls") == 1


def test_display_refresh_does_not_automatically_dispatch_full_engine():
    source = (ROOT / "viewer_dashboard.py").read_text(encoding="utf-8")
    assert "Refresh displayed predictions" in source
    assert "st.cache_data.clear()" in source
    assert "st.rerun()" in source
    assert "requests.post(" not in source
    cloud = (ROOT / "cloud_refresh_ui.py").read_text(encoding="utf-8")
    assert "Run Full Prediction Refresh" in cloud
    assert "st.button(" in cloud
