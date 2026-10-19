"""ATP market snapshot contract: fictional data only; never use a real API key."""
import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from tennis_odds_viewer import match_market, read_odds, validate_snapshot

NOW = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)


def fixture():
    return {
        "event_id": "fixture_one", "sport_key": "tennis_atp_paris_masters",
        "tournament": "Paris Masters", "commence_time_utc": "2026-10-21T11:30:00Z",
        "player_a_name": "Alpha Example", "player_b_name": "Beta Example",
        "market_probability_a": .54, "market_probability_b": .46,
        "market_bookmaker_count": 3,
    }


def mock_snapshot():
    return {
        "schema_version": 1, "provider": "The Odds API",
        "fetched_at_utc": "2026-10-19T07:30:00Z",
        "region": "au", "market": "h2h",
        "method": "Median across bookmakers after removing each bookmaker's two-way margin",
        "prediction_status": "none", "events": [fixture()],
    }


def _write(tmp_path, content):
    folder = tmp_path / "published"
    folder.mkdir(exist_ok=True)
    (folder / "atp_odds_snapshot.json").write_text(json.dumps(content), encoding="utf-8")


def test_no_snapshot_does_not_make_up_tennis_fixtures(tmp_path):
    events, stamp, status = read_odds(tmp_path, NOW)
    assert events == [] and stamp is None and status == "not_published"


def test_only_real_future_tennis_events_displayed(tmp_path):
    data = mock_snapshot()
    _write(tmp_path, data)
    events, stamp, status = read_odds(tmp_path, NOW)
    assert status == "ready"
    assert len(events) == 1
    assert stamp.year == 2026
    assert events[0]["market_probability_a"] == pytest.approx(.54)
    later = datetime(2026, 10, 22, tzinfo=timezone.utc)
    assert read_odds(tmp_path, later)[2] == "no_upcoming"


@pytest.mark.parametrize("mutator", [
    lambda x: x.update(apiKey="PRIVATE"),
    lambda x: x["events"][0].update(bookmakers=[{"price": 1.9}]),
    lambda x: x["events"][0].update(sport_key="tennis_wta_us_open"),
    lambda x: x["events"][0].update(player_b_name=x["events"][0]["player_a_name"]),
    lambda x: x["events"][0].update(market_probability_a=.9),
    lambda x: x["events"][0].update(market_probability_a=None),
    lambda x: x["events"][0].update(market_bookmaker_count=-1),
    lambda x: x["events"][0].update(commence_time_utc="2026-10-21T11:30:00"),
    lambda x: x.update(prediction_status="approved"),
    lambda x: x.update(region="us"),
    lambda x: x.update(fetched_at_utc="2070-01-01T00:00:00Z"),
])
def test_rejects_unsafe_or_false_market_data(mutator):
    data = mock_snapshot()
    mutator(data)
    with pytest.raises(ValueError):
        validate_snapshot(data, NOW)


def test_api_only_events_are_not_claimed_as_market_probs():
    data = mock_snapshot()
    data["events"][0].update(
        market_probability_a=None, market_probability_b=None,
        market_bookmaker_count=0,
    )
    rows, _ = validate_snapshot(data, NOW)
    assert rows[0]["market_probability_a"] is None


def test_missing_data_is_not_deemed_prediction_comparison():
    event, _ = validate_snapshot(mock_snapshot(), NOW)
    assert match_market(event[0], None) is None
    assert match_market(event[0], pd.DataFrame()) is None


def test_compares_only_exact_authorised_match_identity_and_orientation():
    event, _ = validate_snapshot(mock_snapshot(), NOW)
    row = event[0]
    model = pd.DataFrame([{
        "fixture_id": row["event_id"], "model": "ATP Hybrid",
        "kickoff_utc": row["commence_time_utc"], "player_a_name": "Alpha Example",
        "player_b_name": "Beta Example",
        "p_player_a": .62, "p_player_b": .38,
    }])
    assert match_market(row, model) == pytest.approx(8.0)
    flipped = model.copy()
    flipped["player_a_name"] = "Beta Example"
    flipped["player_b_name"] = "Alpha Example"
    flipped["p_player_a"] = .38
    flipped["p_player_b"] = .62
    assert match_market(row, flipped) == pytest.approx(8.0)
    wrong_id = model.copy()
    wrong_id["fixture_id"] = "different_event"
    assert match_market(row, wrong_id) is None
    wrong_start = model.copy()
    wrong_start["kickoff_utc"] = pd.Timestamp("2026-10-22T11:30:00Z")
    assert match_market(row, wrong_start) is None
    wrong_person = model.copy()
    wrong_person["player_a_name"] = "A Different Alpha"
    assert match_market(row, wrong_person) is None
    wrong_model = model.copy()
    wrong_model["model"] = "Surface Elo"
    assert match_market(row, wrong_model) is None


def test_public_football_code_and_credentials_remain_independent():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    tennis = (root / "tennis_viewer.py").read_text()
    assert "tennis_odds_viewer.show_market(root, frame if status == \"ready\" else None)" in tennis
    odds = (root / "tennis_odds_viewer.py").read_text()
    assert "requests." not in odds
    assert "THE_ODDS_API_KEY" not in odds
    assert "api.the-odds-api.com" not in odds
    assert "football" not in odds.lower()
