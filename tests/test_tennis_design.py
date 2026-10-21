import pandas as pd
from tennis_design import prediction_for, pick_html, card_html, flag_url


def fixture():
    return {"fixture_id": 42, "tournament": "Example - Lyon", "surface": "Indoor hard", "round": "First",
            "start_time_utc": "2026-10-21T12:00:00Z", "player_a_id": 1, "player_b_id": 2,
            "player_a_name": "Alpha Example", "player_b_name": "Beta Example", "player_a_country": "AUS", "player_b_country": "ITA"}


def forecast():
    return pd.DataFrame([{"fixture_id": 42, "event_name": "Example - Lyon", "surface": "Hard", "kickoff_utc": "2026-10-21T12:00:00Z", "model": "ATP Hybrid", "player_a_id": 1, "player_b_id": 2, "player_a_name": "Alpha Example", "player_b_name": "Beta Example", "p_player_a": .64, "p_player_b": .36}])


def test_winner_bound_to_exact_identity_and_time():
    row, frame = fixture(), forecast()
    pick = prediction_for(row, frame)
    assert pick["winner"] == "Alpha Example"
    assert "64.0%" in pick_html(row, pick)
    for field, wrong in (("fixture_id", 43), ("player_a_id", 99), ("player_a_name", "Different Alpha"), ("kickoff_utc", "2026-10-22T12:00:00Z"), ("event_name", "Another Open")):
        bad = frame.copy()
        bad[field] = wrong
        assert prediction_for(row, bad) is None


def test_player_orientation_is_respected():
    frame = forecast()
    frame[["player_a_id", "player_b_id"]] = [[2, 1]]
    frame[["player_a_name", "player_b_name"]] = [["Beta Example", "Alpha Example"]]
    frame[["p_player_a", "p_player_b"]] = [[.36, .64]]
    assert prediction_for(fixture(), frame)["p_a"] == .64


def test_no_forecast_never_invents_winner():
    row = fixture()
    assert prediction_for(row, None) is None
    text = card_html(row, "Wed 21 Oct", None)
    assert "Prediction pending" in text and "50.0%" not in text
    assert "au.png" in text and "it.png" in text
    assert flag_url("UNKNOWN") is None


def test_fixture_labels_are_html_escaped():
    row = fixture()
    row["player_a_name"] = '<script>alert("x")</script>'
    text = card_html(row, "Wed 21 Oct", None)
    assert "<script>" not in text and "&lt;script&gt;" in text


def test_country_optional_but_never_arbitrary_html():
    from test_tennis_fixtures_viewer import snapshot, NOW
    from tennis_fixtures_viewer import validate_snapshot
    import pytest
    data = snapshot()
    data["events"][0]["player_a_country"] = "AUS"
    assert validate_snapshot(data, NOW)[0][0]["player_a_country"] == "AUS"
    data["events"][0]["player_a_country"] = '<script>'
    with pytest.raises(ValueError):
        validate_snapshot(data, NOW)


def test_missing_prediction_explains_dataset_counts_only_for_exact_identity():
    from tennis_design import pending_reason
    row=fixture()
    item={key:row[key] for key in ('fixture_id','player_a_id','player_b_id','player_a_name','player_b_name','start_time_utc')}
    item['prior_matches']=[21,0]
    metadata={'excluded_fixtures':[item]}
    reason=pending_reason(row,metadata)
    assert 'Beta Example: 0 recorded' in reason and 'our dataset' in reason and 'at least 5' in reason
    row['_prediction_unavailable_reason']=reason
    assert reason in pick_html(row,None)
    item['player_b_id']=999
    assert '0 recorded' not in pending_reason(row,metadata)


def test_time_change_keeps_pre_match_forecast_but_not_changed_matchup():
    row, frame = fixture(), forecast()
    frame['forecast_issued_at_utc'] = '2026-10-20T00:00:00Z'
    row['start_time_utc'] = '2026-10-21T12:30:00Z'
    pick = prediction_for(row, frame)
    assert pick['p_a'] == .64 and pick['start_updated']
    assert 'Scheduled start updated' in pick_html(row, pick)
    row['player_a_id'] = 99
    assert prediction_for(row, frame) is None
    row = fixture(); row['start_time_utc'] = '2026-10-22T12:00:00Z'
    assert prediction_for(row, frame) is None
    row = fixture(); row['start_time_utc'] = '2026-10-20T00:00:00Z'
    assert prediction_for(row, frame) is None
