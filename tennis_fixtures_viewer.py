"""Static SportsAPI365 ATP Tour fixtures; no credentials or network calls."""
import json
import re
from html import escape
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT_KEYS = {"schema_version", "provider", "fetched_at_utc", "coverage_complete", "dates", "events"}
EVENT_KEYS = {"fixture_id", "tournament", "tournament_id", "rank_id", "surface", "round", "start_time_utc", "player_a_id", "player_b_id", "player_a_name", "player_b_name"}
OPTIONAL_EVENT_KEYS = {"player_a_country", "player_b_country"}
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
        if not isinstance(row, dict) or not EVENT_KEYS.issubset(row) or set(row) - EVENT_KEYS - OPTIONAL_EVENT_KEYS:
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
        for field in OPTIONAL_EVENT_KEYS:
            value = row.get(field)
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[A-Z]{3}", value)):
                raise ValueError("Invalid country code")
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
        # Country cache requires BOTH exact provider ID and full name.
        try:
            countries=json.loads((Path(root)/"published"/"atp_player_countries.json").read_text())
            if countries.get("schema_version")==1:
                for row in rows:
                    for side in ("a","b"):
                        entry=countries.get("players",{}).get(str(row[f"player_{side}_id"]),{})
                        code=entry.get("country")
                        if not row.get(f"player_{side}_country") and entry.get("name")==row[f"player_{side}_name"] and isinstance(code,str) and re.fullmatch(r"[A-Z]{3}",code):
                            row[f"player_{side}_country"]=code
        except (OSError,ValueError,TypeError,AttributeError):
            pass
    except (ValueError, TypeError, KeyError, OSError):
        return [], {}, "invalid"
    return rows, {"stamp": stamp, "complete": data["coverage_complete"], "dates": data["dates"]}, "ready" if rows else "no_upcoming"


def display_rows(rows):
    return [{
        "Match": r["player_a_name"] + " vs " + r["player_b_name"],
        "Sydney start": timestamp(r["start_time_utc"]).astimezone(ZoneInfo("Australia/Sydney")).strftime("%a %d %b, %I:%M %p"),
        "Tournament": r["tournament"], "Surface": r["surface"], "Round": r["round"],
    } for r in rows]


def show_fixtures(root, forecasts=None):
    import streamlit as st
    from tennis_design import (inject_style, tournament_mark, player_html,
                               prediction_for, pick_html, tile_label, card_html)
    inject_style(root)
    from sport_icons import TENNIS
    st.markdown('<div class="atp-hero"><img class="atp-tour-logo" src="https://upload.wikimedia.org/wikipedia/commons/3/3f/ATP_Tour_logo.svg" alt="ATP Tour logo"><div class="atp-hero-icon">'+TENNIS+'<'+ '/div><div><h2>ATP Men’s Singles</h2><p>Upcoming matches · Sydney times · Match-winner outlook</p></div></div>', unsafe_allow_html=True)
    rows, metadata, status = read_fixtures(root)
    st.markdown("### Upcoming ATP matches")
    if status == "not_published":
        st.info("ATP fixture snapshot is being prepared.")
        return
    if status == "invalid":
        st.warning("ATP fixtures could not be verified. Please check back after the next update.")
        return
    st.caption("Updated " + metadata["stamp"].astimezone(ZoneInfo("Australia/Sydney")).strftime("%d %b, %I:%M %p Sydney") + " · Scheduled times may change")
    if not metadata["complete"]:
        st.info("Partial fixture list — more matches may be scheduled. The next full refresh will expand coverage.")
    if (datetime.now(timezone.utc) - metadata["stamp"]).total_seconds() > 86400:
        st.warning("This fixture snapshot is over 24 hours old.")
    if not rows:
        st.info("No upcoming ATP matches remain in this snapshot. This does not mean the ATP calendar is empty.")
        return
    events = sorted({r["tournament"] for r in rows})
    picks = {r["fixture_id"]: prediction_for(r, forecasts) for r in rows}
    from tennis_set_scores import read_set_scores, add_set_pick
    set_scores=read_set_scores(root)
    picks={r["fixture_id"]:add_set_pick(r,picks[r["fixture_id"]],set_scores) for r in rows}
    pick_count = sum(p is not None for p in picks.values())
    st.markdown(f'<div class="atp-stats"><div><b>{len(rows)}</b><span>upcoming matches</span></div><div><b>{len(events)}</b><span>tournaments</span></div><div><b>{pick_count}</b><span>validated match picks</span></div></div>', unsafe_allow_html=True)
    choice = st.selectbox("ATP tournament", ["All tournaments"] + events, key="atp_fixture_tournament")
    selected = rows if choice == "All tournaments" else [r for r in rows if r["tournament"] == choice]
    labels = {r["fixture_id"]: timestamp(r["start_time_utc"]).astimezone(ZoneInfo("Australia/Sydney")).strftime("%a %d %b, %I:%M %p") for r in selected}
    selection_key = "atp_selected_fixture"
    if st.session_state.get(selection_key) not in labels:
        st.session_state[selection_key] = selected[0]["fixture_id"]
    def choose(identity):
        st.session_state[selection_key] = identity
    st.caption("Choose a match · Swipe or scroll for more fixtures")
    with st.container(horizontal=True, wrap=False, key="atp_fixture_tiles"):
        for row in selected:
            st.button(tile_label(row, labels[row["fixture_id"]]), key="atp_tile_"+str(row["fixture_id"]),
                      width=270, type="primary" if row["fixture_id"] == st.session_state[selection_key] else "secondary",
                      on_click=choose, args=(row["fixture_id"],))
    row = next(r for r in selected if r["fixture_id"] == st.session_state[selection_key])
    st.markdown('<div class="atp-selected-head">'+tournament_mark(row["tournament"])+'<div><h3>'+escape(row["tournament"])+ '</h3><small>'+escape(row["round"])+" · "+escape(row["surface"])+" · "+escape(labels[row["fixture_id"]])+" Sydney</small></div></div>", unsafe_allow_html=True)
    st.markdown('<div class="atp-matchup">'+player_html(row,"a")+'<em>VS</em>'+player_html(row,"b")+'</div>'+pick_html(row,picks[row["fixture_id"]]), unsafe_allow_html=True)
    chosen=picks[row["fixture_id"]]
    if chosen and chosen.get("set_outcomes"):
        st.caption("Set-score probabilities · Best of three · Experimental")
        st.table([{"Player":outcome["winner"],"Sets won–lost":outcome["score"],"Estimated probability":f'{outcome["p"]:.1%}'} for outcome in chosen["set_outcomes"]])
    st.markdown("### All upcoming match picks")
    st.markdown('<div class="atp-card-grid">'+''.join(card_html(r,labels[r["fixture_id"]],picks[r["fixture_id"]],r["fixture_id"]==row["fixture_id"]) for r in selected)+'</div>', unsafe_allow_html=True)
    with st.expander("Compact fixture table"):
        st.dataframe(display_rows(selected), hide_index=True, use_container_width=True)
    st.caption("Source: SportsAPI365 · Flags show represented country, using provider records or the checked ATP/ITF player list. Independent predictions site; not affiliated with ATP. Tournament court badges are original identifiers.")
