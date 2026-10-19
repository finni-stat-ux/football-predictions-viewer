"""Static ATP fixture/market display. Never calls The Odds API or holds an API key.

The publisher must manually review/copy a summarised authorised JSON snapshot.
If no real snapshot exists, no odds or fixtures are invented.
"""
from __future__ import annotations

import json
import math
from datetime import timedelta
from pathlib import Path

import pandas as pd

REQUIRED_EVENT = {
    "event_id", "sport_key", "tournament", "commence_time_utc",
    "player_a_name", "player_b_name", "market_probability_a",
    "market_probability_b", "market_bookmaker_count",
}
EXPECTED_TOP = {
    "schema_version", "provider", "fetched_at_utc", "region", "market",
    "method", "prediction_status", "events",
}


def _time(value):
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        raise ValueError("Odds event or publication timestamp must be UTC")
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("Invalid ATP odds date")
    return parsed


def validate_snapshot(data, now=None):
    current = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if current.tzinfo is None:
        raise ValueError("Viewer clock is not timezone-aware")
    current = current.tz_convert("UTC")
    if not isinstance(data, dict) or set(data) != EXPECTED_TOP:
        raise ValueError("Unrecognised or unsafe ATP odds snapshot")
    if (
        data["schema_version"] != 1
        or data["provider"] != "The Odds API"
        or data["region"] != "au" or data["market"] != "h2h"
        or data["prediction_status"] != "none"
        or data["method"] != "Median across bookmakers after removing each bookmaker's two-way margin"
    ):
        raise ValueError("Unsupported ATP provider snapshot")
    stamp = _time(data["fetched_at_utc"])
    if stamp > current or (current - stamp).days > 30:
        raise ValueError("Unreliable provider snapshot timestamp")
    rows = data["events"]
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("Invalid ATP fixture count")
    accepted = []
    seen = set()
    for item in rows:
        if not isinstance(item, dict) or set(item) != REQUIRED_EVENT:
            raise ValueError("Invalid or unsafe ATP fixture row")
        eid = item["event_id"]
        key = item["sport_key"]
        if not (isinstance(eid, str) and 1 <= len(eid) <= 128
                and eid.replace("_", "").replace("-", "").isalnum()):
            raise ValueError("Invalid ATP event ID")
        if not (isinstance(key, str) and key.startswith("tennis_atp_")
                and len(key) <= 128 and all(ch.islower() or ch.isdigit() or ch == "_" for ch in key)):
            raise ValueError("Not an ATP tournament")
        if eid in seen:
            raise ValueError("Duplicate tennis event ID")
        seen.add(eid)
        for label in ("tournament", "player_a_name", "player_b_name"):
            if not isinstance(item[label], str) or not 1 <= len(item[label].strip()) <= 160:
                raise ValueError("Invalid player or tournament label")
        if item["player_a_name"].casefold() == item["player_b_name"].casefold():
            raise ValueError("Same player appears twice")
        kickoff = _time(item["commence_time_utc"])
        if kickoff <= current:
            continue  # Completed matches never appear as upcoming matches.
        if kickoff > current + pd.Timedelta(days=60):
            raise ValueError("Unreasonably distant ATP fixture")
        pa, pb = item["market_probability_a"], item["market_probability_b"]
        count = item["market_bookmaker_count"]
        if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 200:
            raise ValueError("Invalid sportsbook coverage count")
        if pa is None or pb is None:
            if not (pa is None and pb is None and count == 0):
                raise ValueError("Partial bookmaker probability")
        else:
            if not (isinstance(pa, (int, float)) and isinstance(pb, (int, float))
                    and not isinstance(pa, bool) and not isinstance(pb, bool)
                    and math.isfinite(pa) and math.isfinite(pb)
                    and 0 < pa < 1 and 0 < pb < 1
                    and math.isclose(pa + pb, 1., abs_tol=1e-6) and count >= 1):
                raise ValueError("Invalid bookmaker consensus probabilities")
        accepted.append({**item, "commence_time_utc": kickoff})
    return sorted(accepted, key=lambda x: (x["commence_time_utc"], x["event_id"])), stamp


def read_odds(root, now=None):
    file = Path(root) / "published" / "atp_odds_snapshot.json"
    if not file.exists():
        return [], None, "not_published"
    try:
        content = json.loads(file.read_text(encoding="utf-8"))
        rows, stamp = validate_snapshot(content, now)
    except (OSError, ValueError, TypeError, KeyError):
        return [], None, "invalid"
    return rows, stamp, "ready" if rows else "no_upcoming"


def match_market(row, approved_predictions):
    """Only compare genuine validated ATP Hybrid rows with *same provider ID*.

    Exact competitor names and kickoff are checked; no fuzzy name matching that
    might silently attach two similar players or a different tennis event.
    """
    if approved_predictions is None or approved_predictions.empty:
        return None
    selected = approved_predictions[
        approved_predictions.fixture_id.eq(row["event_id"])
        & approved_predictions.model.eq("ATP Hybrid")
    ]
    if len(selected) != 1:
        return None
    model = selected.iloc[0]
    names = (str(model.player_a_name), str(model.player_b_name))
    event_names = (row["player_a_name"], row["player_b_name"])
    if set(names) != set(event_names) or (
        pd.Timestamp(model.kickoff_utc) != row["commence_time_utc"]
    ):
        return None
    if row["market_probability_a"] is None:
        return None
    p_model_a = float(model.p_player_a) if names[0] == event_names[0] else float(model.p_player_b)
    return round(100*(p_model_a - row["market_probability_a"]), 1)


def show_market(root, approved_predictions=None):
    import streamlit as st

    st.subheader("Upcoming ATP fixtures and market reference")
    rows, stamp, status = read_odds(root)
    if status == "not_published":
        st.caption("No ATP fixtures from The Odds API have been published yet. The public website does not call the API.")
        return
    if status == "invalid":
        st.warning("ATP odds snapshot failed verification. No fixtures or prices displayed.")
        return
    if status == "no_upcoming":
        st.info("No upcoming ATP fixtures in the last published provider snapshot.")
        return
    age = pd.Timestamp.now(tz="UTC") - stamp
    quote_fresh = age <= pd.Timedelta(hours=6)
    st.caption(
        "Source: The Odds API. Read-only snapshot at "
        + stamp.strftime("%d %b %Y, %H:%M UTC")
        + ". Match-winner market probabilities exclude each bookmaker's margin."
    )
    if not quote_fresh:
        st.warning("Market snapshot is over six hours old. Price estimates are hidden until refreshed.")
    display = []
    for row in rows:
        record = {
            "Tournament": row["tournament"],
            "Players": row["player_a_name"] + " vs " + row["player_b_name"],
            "Start (Sydney)": row["commence_time_utc"].tz_convert("Australia/Sydney").strftime("%d %b, %I:%M %p"),
        }
        quoted = row["market_probability_a"] is not None and quote_fresh
        record["Market A"] = f"{row['market_probability_a']:.1%}" if quoted else "—"
        record["Market B"] = f"{row['market_probability_b']:.1%}" if quoted else "—"
        record["Books"] = row["market_bookmaker_count"] if quoted else "—"
        diff = match_market(row, approved_predictions) if quoted else None
        record["Hybrid vs market (pp)"] = f"{diff:+.1f}" if diff is not None else "—"
        display.append(record)
    st.dataframe(pd.DataFrame(display), hide_index=True, use_container_width=True)
    st.caption(
        "Bookmaker figures are margin-adjusted market estimates, not the ATP Hybrid. "
        "Hybrid comparison appears only for an independently approved forecast with "
        "an exactly matched event ID, players and start time. No betting recommendation."
    )
