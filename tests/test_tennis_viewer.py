"""Only fictional tennis match records; never published user-visible predictions."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import pytest

from tennis_viewer import read_atp, validated_atp

NOW = datetime(2026, 10, 19, 6, 0, tzinfo=timezone.utc)


def fiction():
    fixture = {
        "fixture_id": "fiction_one", "match_date": "2026-10-22",
        "kickoff_utc": "2026-10-22T11:00:00Z",
        "event_name": "Fictional Cup", "surface": "Hard",
        "player_a_id": "person_a", "player_b_id": "person_b",
        "player_a_name": "Alpha Example", "player_b_name": "Beta Example",
        "serve_return_weight": 0.5,
        "prior_matches_a": 17, "prior_matches_b": 19,
    }
    return pd.DataFrame([
        {**fixture, "model": "Surface Elo", "p_player_a": .6, "p_player_b": .4},
        {**fixture, "model": "Serve/return", "p_player_a": .7, "p_player_b": .3},
        {**fixture, "model": "ATP Hybrid", "p_player_a": .65, "p_player_b": .35},
    ])


def permit():
    return {
        "schema_version": 1,
        "approved_for_publication": True,
        "source_rights_confirmed": True,
        "holdout_checked": True,
        "holdout_matches": 220,
        "published_at_utc": "2026-10-19T02:00:00Z",
        "hybrid_weight_serve_return": .5,
        "history_rights_url": "https://example.com/historical-permission",
        "fixture_rights_url": "https://example.com/fixture-permission",
    }


def test_no_tennis_snapshot_does_not_manufacture_live_picks(tmp_path):
    (tmp_path / "published").mkdir()
    table, metadata, status = read_atp(tmp_path, NOW)
    assert table.empty and metadata == {}
    assert status == "not_published"


def test_exact_two_model_probability_is_checkable():
    output = validated_atp(fiction(), permit(), NOW)
    assert len(output) == 3
    assert output[output.model == "ATP Hybrid"].p_player_a.iloc[0] == pytest.approx(.65)


@pytest.mark.parametrize("key,value", [
    ("approved_for_publication", False),
    ("source_rights_confirmed", False),
    ("holdout_checked", False),
    ("holdout_matches", 12),
    ("history_rights_url", "http://example.com"),
    ("fixture_rights_url", ""),
    ("published_at_utc", "2070-10-19T02:00:00Z"),
    ("hybrid_weight_serve_return", .33),
])
def test_no_unapproved_forecasts_on_public_site(key, value):
    m = permit()
    m[key] = value
    with pytest.raises(ValueError):
        validated_atp(fiction(), m, NOW)


@pytest.mark.parametrize("column,value", [
    ("p_player_a", .999),
    ("p_player_b", -.1),
    ("serve_return_weight", .25),
    ("prior_matches_a", 2),
    ("surface", "Ice"),
    ("match_date", "wrong"),
])
def test_invalid_match_data_rejected(column, value):
    f = fiction()
    f.loc[0, column] = value
    with pytest.raises(ValueError):
        validated_atp(f, permit(), NOW)


def test_cannot_falsify_hybrid_or_omit_component():
    f = fiction()
    f.loc[f.model.eq("ATP Hybrid"), ["p_player_a", "p_player_b"]] = (.9, .1)
    with pytest.raises(ValueError, match="Unreproducible"):
        validated_atp(f, permit(), NOW)
    no_serve = fiction().loc[lambda t: ~t.model.eq("Serve/return")]
    with pytest.raises(ValueError, match="requires"):
        validated_atp(no_serve, permit(), NOW)


def test_completed_games_never_count_as_upcoming():
    later = datetime(2026, 10, 23, 6, 0, tzinfo=timezone.utc)
    assert validated_atp(fiction(), permit(), later).empty


def test_partial_publication_rejected(tmp_path):
    folder = tmp_path / "published"
    folder.mkdir()
    fiction().to_csv(folder / "atp_predictions.csv", index=False)
    assert read_atp(tmp_path, NOW)[2] == "incomplete"
    (folder / "atp_metadata.json").write_text(json.dumps({**permit(), "approved_for_publication": False}))
    assert read_atp(tmp_path, NOW)[2] == "invalid"


def test_existing_football_remains_default_when_tennis_unpublished():
    root = Path(__file__).resolve().parents[1]
    source = (root / "viewer_dashboard.py").read_text()
    assert 'default="Football"' in source
    assert 'if sport == "ATP Men\'s Singles":' in source
    assert "tennis_viewer.show_atp(ROOT)" in source
    assert "if predictions.empty:" in source


def test_atp_mode_independently_renders_no_data_notice():
    from streamlit.testing.v1 import AppTest

    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "viewer_dashboard.py"), default_timeout=60).run()
    assert not app.exception
    sport = next(x for x in app.get("segmented_control") if x.label == "Sport")
    sport.set_value("ATP Men's Singles").run()
    assert not app.exception
    assert any("ATP Men's Singles" in str(x.value) for x in app.subheader)
    assert any("No licensed" in str(x.value) for x in app.info)
    assert not any("ATP Hybrid" in str(x.value) for x in app.metric)
