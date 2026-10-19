"""Static SportsAPI365 ATP Tour fixtures; no credentials or network calls."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT_KEYS = {"schema_version", "provider", "fetched_at_utc", "coverage_complete", "dates", "events"}
EVENT_KEYS = {"fixture_id", "tournament", "tournament_id", "rank_id", "surface", "round", "start_time_utc", "player_a_id", "player_b_id", "player_a_name", "player_b_name"}
TIERS = {2: "ATP Tour", 3: "Masters", 4: "Grand Slam", 7: "Tour Finals"}


def timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC timestamp required")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_snapshot(data, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Clock must have timezone")
    if not isinstance(data, dict) or set(data) != ROOT_KEYS:
        raise ValueError("Invalid fixture snapshot")
    if data["schema_version"] != 1 or data["provider"] != "SportsAPI365":
        raise ValueError("Invalid fixture provider")
    stamp = timestamp(data["fetched_at_utc"])
    if stamp > now or not isinstance(data["coverage_complete"], bool):
        raise ValueError("Invalid snapshot metadata")
    if not isinstance(data["dates"], list) or not 1 <= len(data["dates"]) <= 7:
        raise ValueError("Invalid date window")
    for date in data["dates"]:
        if datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d") != date:
            raise ValueError("Invalid date")
    if not isinstance(data["events"], list) or len(data["events"]) > 1000:
        raise ValueError("Invalid fixture count")
    seen, upcoming = set(), []
    for row in data["events"]:
        if not isinstance(row, dict) or set(row) != EVENT_KEYS:
            raise ValueError("Invalid fixture fields")
        for field in ("fixture_id", "tournament_id", "player_a_id", "player_b_id"):
            if type(row[field]) is not int or row[field] <= 0:
                raise ValueError("Invalid fixture identity")
        if row["fixture_id"] in seen or row["player_a_id"] == row["player_b_id"]:
            raise ValueError("Duplicate fixture or player")
        seen.add(row["fixture_id"])
        if type(row["rank_id"]) is not int or row["rank_id"] not in TIERS:
            raise ValueError("Not ATP Tour")
        for field in ("tournament", "round", "player_a_name", "player_b_name"):
            if not isinstance(row[field], str) or not 1 <= len(row[field].strip()) <= 160:
                raise ValueError("Invalid fixture label")
        names = (row["player_a_name"], row["player_b_name"])
        if names[0].casefold() == names[1].casefold() or any(m in n for n in names for m in ("/", " & ", " + ")):
            raise ValueError("Not distinct singles players")
        if row["surface"] not in ("Hard", "Indoor hard", "Clay", "Grass", "Carpet", "Unknown"):
            raise ValueError("Unknown surface code")
        start = timestamp(row["start_time_utc"])
        if start.date().isoformat() not in data["dates"]:
            raise ValueError("Fixture outside collection window")
        if start > now:
            upcoming.append(row)
    return sorted(upcoming, key=lambda r: (r["start_time_utc"], r["fixture_id"])), stamp


def read_fixtures(root, now=None):
    path = Path(root) / "published" / "atp_fixtures.json"
    if not path.exists():
        return [], {}, "not_published"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows, stamp = validate_snapshot(data, now)
    except (ValueError, TypeError, KeyError, OSError):
        return [], {}, "invalid"
    return rows, {"stamp": stamp, "complete": data["coverage_complete"], "dates": data["dates"]}, "ready" if rows else "no_upcoming"


def display_rows(rows):
    return [{
        "Match": r["player_a_name"] + " vs " + r["player_b_name"],
        "Sydney start": timestamp(r["start_time_utc"]).astimezone(ZoneInfo("Australia/Sydney")).strftime("%a %d %b, %I:%M %p"),
        "Tournament": r["tournament"], "Surface": r["surface"], "Round": r["round"],
    } for r in rows]


def show_fixtures(root):
    import streamlit as st
    rows, metadata, status = read_fixtures(root)
    st.markdown("### Upcoming ATP matches")
    if status == "not_published":
        st.info("ATP fixture snapshot is being prepared.")
        return
    if status == "invalid":
        st.warning("ATP fixtures could not be verified. Please check back after the next update.")
        return
    st.caption("Source: SportsAPI365 · Updated " + metadata["stamp"].astimezone(ZoneInfo("Australia/Sydney")).strftime("%d %b, %I:%M %p Sydney") + " · Scheduled times may change")
    if not metadata["complete"]:
        st.info("Partial fixture list — more matches may be scheduled. The next full refresh will expand coverage.")
    if (datetime.now(timezone.utc) - metadata["stamp"]).total_seconds() > 86400:
        st.warning("This fixture snapshot is over 24 hours old.")
    if not rows:
        st.info("No upcoming ATP matches remain in this snapshot. This does not mean the ATP calendar is empty.")
        return
    events = sorted({r["tournament"] for r in rows})
    choice = st.selectbox("ATP tournament", ["All tournaments"] + events, key="atp_fixture_tournament")
    selected = rows if choice == "All tournaments" else [r for r in rows if r["tournament"] == choice]
    st.dataframe(display_rows(selected), hide_index=True, use_container_width=True)
    st.caption("Men’s singles · ATP Tour, Masters, Grand Slams and Tour Finals · Fixtures only; winner predictions will appear separately when ready.")
