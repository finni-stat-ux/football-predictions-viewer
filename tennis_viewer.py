"""ATP winner viewer. Only displays approved, licensed, coherent forecasts.

No tennis data is downloaded here. Without an approved snapshot the page states
that ATP predictions are not yet available, rather than inventing probabilities.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

MODELS = ("Surface Elo", "Serve/return", "ATP Hybrid")
KEYS = (
    "fixture_id", "match_date", "kickoff_utc", "event_name", "surface",
    "player_a_id", "player_b_id", "player_a_name", "player_b_name",
    "model", "p_player_a", "p_player_b", "serve_return_weight",
    "prior_matches_a", "prior_matches_b",
)
IDENTITY = (
    "match_date", "kickoff_utc", "event_name", "surface",
    "player_a_id", "player_b_id", "player_a_name", "player_b_name",
)


def _https(value):
    try:
        url = urlsplit(str(value))
        return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
    except ValueError:
        return False


def validated_atp(frame, metadata, now=None, *, retain_started=False):
    """Never publish stale fixtures, unlicensed data or fabricated hybrids."""
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        raise ValueError("Evaluation clock must be timezone-aware")
    now = now.tz_convert("UTC")
    if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
        raise ValueError("Invalid ATP publication metadata")
    for key in ("approved_for_publication", "source_rights_confirmed", "holdout_checked"):
        if metadata.get(key) is not True:
            raise ValueError("ATP release not authorised or evaluated")
    try:
        holdout_matches = int(metadata.get("holdout_matches", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid ATP holdout sample") from exc
    if holdout_matches < 200:
        raise ValueError("ATP holdout sample gate failed")
    if not all(_https(metadata.get(key, "")) for key in ("history_rights_url", "fixture_rights_url")):
        raise ValueError("ATP source rights not documented")
    stamp = str(metadata.get("published_at_utc", ""))
    if not stamp.endswith(("Z", "+00:00")):
        raise ValueError("ATP snapshot must be published in UTC")
    published = pd.to_datetime(stamp, utc=True, errors="coerce")
    if pd.isna(published) or published > now:
        raise ValueError("Invalid ATP publication timestamp")
    weight = metadata.get("hybrid_weight_serve_return")
    if not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight not in (0, 0.25, 0.5, 0.75, 1.0):
        raise ValueError("Invalid ATP trained blend weight")
    if frame is None or frame.empty or not set(KEYS).issubset(frame.columns):
        raise ValueError("Missing ATP prediction data")
    data = frame.loc[:, list(KEYS)].copy()
    if data.isna().any().any() or data.duplicated(["fixture_id", "model"]).any():
        raise ValueError("Incomplete or duplicate ATP prediction")
    if not data.model.isin(MODELS).all() or not data.surface.isin(("Hard", "Clay", "Grass", "Carpet")).all():
        raise ValueError("Unsupported ATP model or surface")
    if not data.match_date.astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("Match dates must be YYYY-MM-DD")
    if pd.to_datetime(data.match_date, format="%Y-%m-%d", errors="coerce").isna().any():
        raise ValueError("Invalid ATP match dates")
    if not data.kickoff_utc.astype(str).str.contains(r"(?:Z|[+-]\d{2}:\d{2})$", regex=True).all():
        raise ValueError("ATP kickoff needs a timezone offset")
    data["kickoff_utc"] = pd.to_datetime(data.kickoff_utc, utc=True, errors="coerce")
    if data.kickoff_utc.isna().any():
        raise ValueError("Invalid ATP fixture kickoff")
    for name in ("p_player_a", "p_player_b", "serve_return_weight"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    if not data[["p_player_a", "p_player_b"]].apply(lambda c: c.map(math.isfinite)).all().all():
        raise ValueError("Nonfinite ATP probability")
    if not data[["p_player_a", "p_player_b"]].ge(0).all().all() or not data[["p_player_a", "p_player_b"]].le(1).all().all():
        raise ValueError("ATP probabilities outside [0,1]")
    if not ((data.p_player_a + data.p_player_b - 1).abs() <= 1e-6).all():
        raise ValueError("ATP player winner probabilities must sum to one")
    if not data.serve_return_weight.eq(weight).all():
        raise ValueError("ATP model weight does not match release manifest")
    for name in ("prior_matches_a", "prior_matches_b"):
        values = pd.to_numeric(data[name], errors="coerce")
        if values.isna().any() or (values < 5).any() or not values.map(lambda x: float(x).is_integer()).all():
            raise ValueError("Not enough earlier ATP matches for player")
    for _, match in data.groupby("fixture_id"):
        if any(match[column].nunique() != 1 for column in IDENTITY):
            raise ValueError("Conflicting ATP fixture identity")
        if match.player_a_id.iloc[0] == match.player_b_id.iloc[0]:
            raise ValueError("Duplicate ATP players")
        models = set(match.model)
        if "Surface Elo" not in models:
            raise ValueError("ATP match missing Elo baseline")
        if "ATP Hybrid" in models:
            if "Serve/return" not in models or weight == 0:
                raise ValueError("ATP Hybrid requires two independently available models")
            elo = float(match.loc[match.model.eq("Surface Elo"), "p_player_a"].iloc[0])
            sr = float(match.loc[match.model.eq("Serve/return"), "p_player_a"].iloc[0])
            hybrid = float(match.loc[match.model.eq("ATP Hybrid"), "p_player_a"].iloc[0])
            if not math.isclose(hybrid, (1-weight)*elo + weight*sr, abs_tol=1e-6):
                raise ValueError("Unreproducible ATP Hybrid probability")
    visible=(data.kickoff_utc > now) | (retain_started & (data.kickoff_utc > published))
    return data.loc[visible].sort_values(["kickoff_utc", "fixture_id", "model"]).reset_index(drop=True)


def read_atp(root, now=None, *, retain_started=False):
    base = Path(root) / "published"
    csv_path, json_path = base / "atp_predictions.csv", base / "atp_metadata.json"
    if not csv_path.exists() and not json_path.exists():
        return pd.DataFrame(), {}, "not_published"
    if not csv_path.exists() or not json_path.exists():
        return pd.DataFrame(), {}, "incomplete"
    try:
        metadata = json.loads(json_path.read_text(encoding="utf-8"))
        frame = validated_atp(pd.read_csv(csv_path), metadata, now, retain_started=retain_started)
    except (ValueError, TypeError, KeyError, OSError, pd.errors.ParserError):
        return pd.DataFrame(), {}, "invalid"
    return frame, metadata, "ready" if not frame.empty else "no_upcoming"


def show_atp(root):
    import streamlit as st

    frame, metadata, status = read_atp(root, retain_started=True)
    import tennis_fixtures_viewer
    tennis_fixtures_viewer.show_fixtures(root, frame if status == "ready" else None, metadata)
    from cloud_refresh_ui import show_cloud_refresh
    show_cloud_refresh(atp=True)
    # The independent market snapshot never triggers a provider API call.
    # ATP Hybrid comparisons require an independently approved forecast file.
    import tennis_odds_viewer
    with st.expander("Bookmaker reference (optional)"):
        tennis_odds_viewer.show_market(root, frame if status == "ready" else None)
    def footer():
        st.divider()
        st.caption("Source: SportsAPI365 · Flags show represented country, using provider records or the checked ATP/ITF player list. Independent predictions site; not affiliated with ATP. Tournament court badges are original identifiers.")
        if metadata.get("published_at_utc"):
            st.caption("ATP snapshot published: " + pd.Timestamp(metadata["published_at_utc"]).strftime("%d %b %Y, %H:%M UTC"))
    if status == "not_published":
        st.info("ATP winner predictions are being validated. The fixture list above is separate from model forecasts.")
        footer()
        return
    if status in ("invalid", "incomplete"):
        st.warning("ATP publication failed validation. No tennis probabilities are displayed.")
        footer()
        return
    if status == "no_upcoming":
        st.info("No upcoming ATP matches remain in the last approved snapshot.")
        footer()
        return
    if (pd.Timestamp.now(tz="UTC") - pd.Timestamp(metadata["published_at_utc"])).total_seconds() > 72 * 3600:
        st.warning("ATP forecast snapshot is over 72 hours old. Confirm freshness before use.")
    with st.expander("Models & performance"):
        st.caption("ATP Hybrid combines surface Elo and earlier serve/return form. Set-score estimates use a separate experimental model for supported best-of-three matches.")
        if metadata.get("training_through"):
            st.caption("Historical results through "+str(metadata["training_through"]))
        if metadata.get("evaluation"):
            st.dataframe(pd.DataFrame(metadata["evaluation"]),hide_index=True,use_container_width=True)
    footer()
