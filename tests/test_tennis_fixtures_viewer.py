import copy
import json
from datetime import datetime, timezone

import pytest
from tennis_fixtures_viewer import validate_snapshot, read_fixtures, display_rows

NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


def snapshot():
    return {"schema_version": 1, "provider": "SportsAPI365", "fetched_at_utc": "2026-10-19T10:00:00Z",
            "coverage_complete": False, "dates": ["2026-10-19"], "events": [{
                "fixture_id": 42, "tournament": "Example Open", "tournament_id": 9, "rank_id": 2,
                "surface": "Indoor hard", "round": "First", "start_time_utc": "2026-10-19T16:00:00Z",
                "player_a_id": 1, "player_b_id": 2, "player_a_name": "Alpha Example", "player_b_name": "Beta Example"}]}


def test_sydney_date_rollover():
    rows, stamp = validate_snapshot(snapshot(), NOW)
    assert display_rows(rows)[0]["Sydney start"] == "Tue 20 Oct, 03:00 AM"


@pytest.mark.parametrize("change", [
    lambda s: s.update(apiKey="secret"),
    lambda s: s["events"][0].update(rank_id=1),
    lambda s: s["events"][0].update(player_b_id=1),
    lambda s: s["events"][0].update(player_b_name="One / Two"),
    lambda s: s["events"][0].update(start_time_utc="2026-10-19T16:00:00"),
    lambda s: s.update(fetched_at_utc="2030-01-01T00:00:00Z"),
    lambda s: s["events"].append(copy.deepcopy(s["events"][0])),
])
def test_invalid_data_rejected(change):
    data = snapshot()
    change(data)
    with pytest.raises(ValueError):
        validate_snapshot(data, NOW)


def test_expired_fixture_hidden():
    assert validate_snapshot(snapshot(), datetime(2026, 10, 20, tzinfo=timezone.utc))[0] == []


def test_snapshot_reader(tmp_path):
    assert read_fixtures(tmp_path, NOW)[2] == "not_published"
    folder = tmp_path / "published"
    folder.mkdir()
    (folder / "atp_fixtures.json").write_text(json.dumps(snapshot()))
    rows, metadata, status = read_fixtures(tmp_path, NOW)
    assert status == "ready" and not metadata["complete"] and len(rows) == 1


def test_streamlit_fixture_screen(tmp_path):
    from streamlit.testing.v1 import AppTest
    folder = tmp_path / "published"
    folder.mkdir()
    data = snapshot()
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    future = now + timedelta(hours=6)
    data["dates"] = [future.date().isoformat()]
    data["fetched_at_utc"] = (now-timedelta(minutes=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    data["events"][0]["start_time_utc"] = future.isoformat(timespec="seconds").replace("+00:00", "Z")
    (folder / "atp_fixtures.json").write_text(json.dumps(data))
    app = AppTest.from_string(f"from tennis_fixtures_viewer import show_fixtures\nshow_fixtures({str(tmp_path)!r})").run()
    assert not app.exception
    assert len(app.dataframe) == 1
    assert "Partial fixture list" in app.info[0].value


def test_day_options_use_sydney_midnight_and_monday_to_sunday_order():
    from tennis_fixtures_viewer import day_options
    rows=[{'start_time_utc':'2026-10-19T10:30:00Z'}, # Monday Sydney
          {'start_time_utc':'2026-10-19T13:30:00Z'}, # Tuesday Sydney
          {'start_time_utc':'2026-10-25T14:00:00Z'}] # Following Monday outside window
    days=day_options(rows,datetime(2026,10,19,9,tzinfo=timezone.utc))
    assert [day[1] for day in days]==['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    assert days[0]==('2026-10-19','Monday',1)
    assert days[1]==('2026-10-20','Tuesday',1)
    assert sum(day[2] for day in days)==2
