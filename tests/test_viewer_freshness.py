"""Deterministic checks of forecast freshness independent of CI clock."""
from viewer_freshness import hours_since_forecast, stale_forecast_notice


def test_fresh_snapshot_has_no_warning():
    assert hours_since_forecast(
        "2026-10-18T00:00:00Z", "2026-10-18T23:00:00Z"
    ) == 23
    assert stale_forecast_notice(
        "2026-10-18T00:00:00Z", "2026-10-18T23:00:00Z"
    ) is None


def test_stale_forecast_warns_and_explains_real_refresh():
    notice = stale_forecast_notice(
        "2026-10-15T11:24:57+00:00", "2026-10-18T11:24:57Z"
    )
    assert "3 days ago" in notice
    assert "Cloud Prediction Refresh" in notice
    assert "only reloads" in notice


def test_utc_offsets_and_bad_timestamps():
    assert hours_since_forecast(
        "2026-10-18T10:00:00+11:00", "2026-10-18T00:00:00Z"
    ) == 1
    assert hours_since_forecast("not-a-date", "2026-10-18T00:00:00Z") is None
    assert "cannot be verified" in stale_forecast_notice(
        "invalid", "2026-10-18T00:00:00Z"
    )


def test_future_snapshot_does_not_warn():
    assert hours_since_forecast(
        "2026-10-19T00:00:00Z", "2026-10-18T00:00:00Z"
    ) == 0
    assert stale_forecast_notice(
        "2026-10-19T00:00:00Z", "2026-10-18T00:00:00Z"
    ) is None
