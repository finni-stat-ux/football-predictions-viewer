"""Archived, strictly pre-match football picks compared with independently verified FT results.

This is an observation ledger, not a replay of predictions fitted after matches.
Only source-committed probabilities can be included; never recompute old picks.
"""
from __future__ import annotations

import math
import re
from urllib.parse import urlsplit

import pandas as pd

LEAGUES = ("EPL", "Championship")
MODELS = ("Hybrid", "Dixon-Coles", "XGBoost", "Matrix")

# Display labels match the main predictions page; source-data IDs stay unchanged.
COMPETITION_NAMES = {"EPL": "English Premier League", "Championship": "EFL Championship"}


def competition_label(value: str) -> str:
    return COMPETITION_NAMES.get(value, value)


def model_label(value: str) -> str:
    return "Matrix — Experimental" if value == "Matrix" else value
IDENTITY = ("date", "competition", "HomeTeam", "AwayTeam")
PROBABILITIES = ("p_home_win", "p_draw", "p_away_win")
REQUIRED = (
    *IDENTITY, "model", *PROBABILITIES, "most_likely_score",
    "actual_home_goals", "actual_away_goals", "forecast_published_at_utc",
    "forecast_commit", "result_source", "result_source_url",
)


def validated_history(raw: pd.DataFrame) -> pd.DataFrame:
    """Reject ambiguous, late, invalid or fabricated forecast/result pairings.

    Historical forecasts without exact kickoff times must predate **midnight
    UTC on the fixture date**, which is deliberately more conservative than
    allowing any forecast published before the actual kickoff.
    """
    if raw is None or raw.empty:
        return pd.DataFrame(columns=[*REQUIRED, "actual_result", "pick",
                                     "pick_probability", "correct_pick", "exact_score_hit"])
    if not set(REQUIRED).issubset(raw.columns):
        raise ValueError("Historical results snapshot lacks required fields")
    frame = raw.loc[:, list(REQUIRED)].copy()
    if frame[list(IDENTITY) + ["model"]].isna().any().any():
        raise ValueError("Historical fixture identity is incomplete")
    if frame.duplicated([*IDENTITY, "model"]).any():
        raise ValueError("Duplicate historical forecast for a fixture and model")
    if not frame["competition"].isin(LEAGUES).all() or not frame["model"].isin(MODELS).all():
        raise ValueError("Unrecognized competition or independent model")
    if not frame["date"].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("Historical fixture dates must be ISO dates")
    dates = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    published = pd.to_datetime(frame["forecast_published_at_utc"], errors="coerce", utc=True)
    if dates.isna().any() or published.isna().any() or not (published < dates).all():
        raise ValueError("Forecast publication is missing or not strictly before the fixture date")
    if not frame["forecast_commit"].astype(str).str.fullmatch(r"[0-9a-f]{40}").all():
        raise ValueError("Historical forecasts need an immutable public Git commit")
    for value in frame["result_source_url"]:
        url = urlsplit(str(value))
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError("A validated HTTPS result-source URL is required")
    if frame["result_source"].isna().any():
        raise ValueError("Result provider must be identified")
    for name in ("actual_home_goals", "actual_away_goals"):
        col = pd.to_numeric(frame[name], errors="coerce")
        if col.isna().any() or not col.map(lambda n: math.isfinite(n) and n >= 0 and float(n).is_integer()).all():
            raise ValueError("Historical results require nonnegative full-time integer goals")
        frame[name] = col.astype(int)
    for name in PROBABILITIES:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
        if frame[name].isna().any() or not frame[name].map(math.isfinite).all() or not frame[name].between(0, 1).all():
            raise ValueError("Invalid historical prediction probability")
    if not ((frame[list(PROBABILITIES)].sum(axis=1) - 1).abs() <= 0.00001).all():
        raise ValueError("Historical 1X2 probabilities do not sum to one")
    if not frame["most_likely_score"].astype(str).str.fullmatch(r"\d{1,2}-\d{1,2}").all():
        raise ValueError("Invalid archived most-likely scoreline")
    grouped = frame.groupby(list(IDENTITY), dropna=False)
    for name in ("actual_home_goals", "actual_away_goals"):
        if (grouped[name].nunique() != 1).any():
            raise ValueError("Conflicting final results for the same fixture")

    frame["actual_result"] = "D"
    frame.loc[frame.actual_home_goals > frame.actual_away_goals, "actual_result"] = "H"
    frame.loc[frame.actual_home_goals < frame.actual_away_goals, "actual_result"] = "A"
    choices = ("H", "D", "A")
    probability_cols = list(PROBABILITIES)
    frame["pick"] = frame[probability_cols].idxmax(axis=1).map(
        dict(zip(probability_cols, choices))
    )
    frame["pick_probability"] = frame[probability_cols].max(axis=1)
    frame["correct_pick"] = frame["pick"].eq(frame["actual_result"])
    frame["exact_score_hit"] = frame["most_likely_score"].eq(
        frame["actual_home_goals"].astype(str) + "-" + frame["actual_away_goals"].astype(str)
    )
    return frame.sort_values(["date", "competition", "HomeTeam", "model"],
                             ascending=[False, True, True, True]).reset_index(drop=True)


def _pick_text(row) -> str:
    if row["pick"] == "H":
        return str(row["HomeTeam"])
    if row["pick"] == "A":
        return str(row["AwayTeam"])
    return "Draw"


def show_historical_matches(source: pd.DataFrame, default_league: str) -> None:
    """One mobile-friendly expander for archived real games and model choices."""
    import streamlit as st

    with st.expander("Historical Match Results · predictions vs final scores"):
        st.caption(
            "A dated record of what the model actually published before each game, "
            "joined to verified 90-minute results. Not a reconstructed forecast."
        )
        try:
            history = validated_history(source)
        except (ValueError, TypeError) as error:
            st.warning("Historical match records did not pass validation; no results are shown.")
            return
        if history.empty:
            st.info(
                "There are no verified pre-match forecast/result pairs published yet. "
                "The retrospective model backtests remain available in Models & performance."
            )
            return

        leagues = ["All competitions", *LEAGUES]
        selected_league = st.selectbox(
            "Historical competition", leagues,
            index=leagues.index(default_league) if default_league in leagues else 0,
            format_func=competition_label,
            key="history_league"
        )
        visible = history if selected_league == "All competitions" else history[history.competition == selected_league]
        available_models = [name for name in MODELS if name in set(visible.model)]
        model = st.selectbox(
            "Historical model", available_models,
            index=available_models.index("Hybrid") if "Hybrid" in available_models else 0,
            format_func=model_label,
            key="history_model"
        )
        visible = visible[visible.model == model]
        dates = ["All dates", *sorted(visible.date.unique(), reverse=True)]
        selected_date = st.selectbox("Historical match date", dates, key="history_date")
        if selected_date != "All dates":
            visible = visible[visible.date == selected_date]
        if visible.empty:
            st.info("No verified archived predictions match these filters.")
            return

        samples = len(visible)
        result_hits = int(visible.correct_pick.sum())
        score_hits = int(visible.exact_score_hit.sum())
        st.caption(
            f"{samples} verified historical matches · "
            f"Match-winner picks correct: {result_hits}/{samples} ({result_hits / samples:.1%}) · "
            f"Exact most-likely scores: {score_hits}/{samples}. "
            "Small samples are not evidence of future performance."
        )

        entries = []
        for _, item in visible.iterrows():
            entries.append({
                "Date (UTC)": item["date"],
                "Match": f"{item['HomeTeam']} vs {item['AwayTeam']}",
                "Predicted": _pick_text(item),
                "Pick probability": f"{item['pick_probability']:.1%}",
                "Actual FT": f"{item['actual_home_goals']}-{item['actual_away_goals']}",
                "Winner pick": "Correct" if item["correct_pick"] else "Incorrect",
                "Score pick": "Correct" if item["exact_score_hit"] else "Incorrect",
            })
        st.dataframe(pd.DataFrame(entries), hide_index=True, width="stretch")

        labels = {
            f"{item.date} · {item.HomeTeam} vs {item.AwayTeam}": i
            for i, item in visible.reset_index(drop=True).iterrows()
        }
        selected_name = st.selectbox("Completed match", list(labels), key="history_match")
        selected = visible.iloc[labels[selected_name]]
        st.markdown(
            f"**{selected['HomeTeam']} {selected['actual_home_goals']}–"
            f"{selected['actual_away_goals']} {selected['AwayTeam']}** · Full time"
        )
        st.write(
            f"**{model} predicted:** {_pick_text(selected)} "
            f"({selected['pick_probability']:.1%}) — "
            f"{'correct outcome' if selected['correct_pick'] else 'incorrect outcome'}"
        )
        breakdown = pd.DataFrame([{
            "Home win": f"{selected['p_home_win']:.1%}",
            "Draw": f"{selected['p_draw']:.1%}",
            "Away win": f"{selected['p_away_win']:.1%}",
            "Top exact score": str(selected["most_likely_score"]),
        }])
        st.dataframe(breakdown, hide_index=True, width="stretch")
        commit = selected["forecast_commit"]
        snapshot_link = (
            "https://github.com/finni-stat-ux/football-predictions-viewer/blob/"
            + commit + "/published/predictions.csv"
        )
        st.caption(
            "Published forecast (UTC): "
            + pd.Timestamp(selected["forecast_published_at_utc"]).strftime("%d %b %Y, %H:%M")
            + " · Archived snapshot, not recalculated from the final score."
        )
        st.markdown(
            f"[Original saved forecast]({snapshot_link}) · "
            f"[Verified result — {selected['result_source']}]({selected['result_source_url']})"
        )
        st.caption(
            "For this initial archive, only forecasts published before midnight UTC "
            "on the match date are eligible. Experimental Matrix forecasts were not "
            "available in the qualifying 15 October snapshot. "
            "W-H-W is a Hybrid interpretation rather than an independent model."
        )
