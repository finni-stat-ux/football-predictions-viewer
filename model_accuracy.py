"""Paired historical Hybrid/Matrix comparison from approved performance snapshots.

Both models must have identical competition/season sample counts.
This is *retrospective* performance, not prospective accuracy or calibration.
"""
from __future__ import annotations

import math
import pandas as pd

REQUIRED = (
    "season", "competition", "model", "matches",
    "1x2_log_loss", "1x2_brier", "1x2_accuracy",
    "exact_score_log_loss", "exact_score_hit_rate",
)
METRICS = tuple(x for x in REQUIRED if x.startswith("1x2_") or x.startswith("exact_score_"))
LEAGUES = ("EPL", "Championship")
MODELS = ("Hybrid", "Matrix")


def paired_season_metrics(raw: pd.DataFrame) -> pd.DataFrame:
    """Accept only season/league observations with valid, matched model samples."""
    columns = list(REQUIRED)
    if raw is None or raw.empty or not set(columns).issubset(raw.columns):
        return pd.DataFrame(columns=columns)
    data = raw.loc[raw.competition.isin(LEAGUES) & raw.model.isin(MODELS), columns].copy()
    if data.duplicated(["competition", "season", "model"]).any():
        return pd.DataFrame(columns=columns)
    for field in ("matches", *METRICS):
        data[field] = pd.to_numeric(data[field], errors="coerce")
    data = data.loc[
        (data.matches > 0) &
        data.matches.notna() &
        data.matches.map(lambda x: math.isfinite(float(x)) and float(x).is_integer())
    ]
    for field in METRICS:
        data = data.loc[data[field].notna() & data[field].map(math.isfinite)]
        data = data.loc[data[field] >= 0]
    for field in ("1x2_accuracy", "exact_score_hit_rate", "1x2_brier"):
        data = data.loc[data[field] <= (3 if field == "1x2_brier" else 1)]
    pairs = []
    for (_, _), group in data.groupby(["competition", "season"]):
        if set(group.model) != set(MODELS) or len(group) != 2:
            continue
        if group.matches.nunique() != 1:
            continue
        pairs.append(group)
    return pd.concat(pairs, ignore_index=True) if pairs else pd.DataFrame(columns=columns)


def compare_leagues(raw: pd.DataFrame) -> pd.DataFrame:
    """Weighted by comparable season match counts; log-loss delta Matrix minus Hybrid."""
    seasons = paired_season_metrics(raw)
    columns = [
        "Competition", "Seasons", "Matches",
        "Hybrid log loss", "Matrix log loss", "Log loss difference",
        "Hybrid accuracy", "Matrix accuracy", "Accuracy difference",
        "Hybrid Brier", "Matrix Brier",
        "Hybrid score loss", "Matrix score loss",
        "Matrix lower-loss seasons",
    ]
    results = []
    for league in LEAGUES:
        frame = seasons[seasons.competition == league]
        if frame.empty:
            continue
        by_model = {name: frame[frame.model == name] for name in MODELS}
        count = int(by_model["Hybrid"].matches.sum())
        if count <= 0:
            continue
        def weighted(model, metric):
            subset = by_model[model]
            return float((subset[metric] * subset.matches).sum() / count)
        hybrid_loss = weighted("Hybrid", "1x2_log_loss")
        matrix_loss = weighted("Matrix", "1x2_log_loss")
        hybrid_accuracy = weighted("Hybrid", "1x2_accuracy")
        matrix_accuracy = weighted("Matrix", "1x2_accuracy")
        season_losses = by_model["Matrix"].merge(
            by_model["Hybrid"], on=["competition", "season", "matches"],
            suffixes=("_matrix", "_hybrid"), validate="one_to_one",
        )
        results.append({
            "Competition": "English Premier League" if league == "EPL" else "EFL Championship",
            "Seasons": len(season_losses),
            "Matches": count,
            "Hybrid log loss": hybrid_loss,
            "Matrix log loss": matrix_loss,
            "Log loss difference": matrix_loss - hybrid_loss,
            "Hybrid accuracy": hybrid_accuracy,
            "Matrix accuracy": matrix_accuracy,
            "Accuracy difference": matrix_accuracy - hybrid_accuracy,
            "Hybrid Brier": weighted("Hybrid", "1x2_brier"),
            "Matrix Brier": weighted("Matrix", "1x2_brier"),
            "Hybrid score loss": weighted("Hybrid", "exact_score_log_loss"),
            "Matrix score loss": weighted("Matrix", "exact_score_log_loss"),
            "Matrix lower-loss seasons": int(
                (season_losses["1x2_log_loss_matrix"] < season_losses["1x2_log_loss_hybrid"]).sum()
            ),
        })
    return pd.DataFrame(results, columns=columns)


def show_league_accuracy(raw: pd.DataFrame) -> None:
    """Compact comparison without implying statistical significance."""
    import streamlit as st
    with st.expander("Model accuracy · Hybrid vs Matrix by league"):
        comparison = compare_leagues(raw)
        if comparison.empty:
            st.info("Matching historical Hybrid and Matrix evaluation data is unavailable.")
            return
        st.caption(
            "Retrospective, chronologically separated seasonal tests. "
            "Each pair uses the same matches; figures below are weighted by match count. "
            "Lower log loss and Brier are better. These are not live results."
        )
        for _, row in comparison.iterrows():
            st.markdown(f"**{row['Competition']}** · {row['Matches']:,} matches, {row['Seasons']} seasons")
            st.dataframe(pd.DataFrame([
                {
                    "Model": "Hybrid",
                    "Result accuracy": f"{row['Hybrid accuracy']:.1%}",
                    "Result log loss": f"{row['Hybrid log loss']:.4f}",
                    "1X2 Brier": f"{row['Hybrid Brier']:.4f}",
                    "Exact-score loss": f"{row['Hybrid score loss']:.4f}",
                },
                {
                    "Model": "Matrix (experimental)",
                    "Result accuracy": f"{row['Matrix accuracy']:.1%}",
                    "Result log loss": f"{row['Matrix log loss']:.4f}",
                    "1X2 Brier": f"{row['Matrix Brier']:.4f}",
                    "Exact-score loss": f"{row['Matrix score loss']:.4f}",
                },
            ]), hide_index=True, use_container_width=True)
            difference = row["Log loss difference"]
            if abs(difference) < 0.0005:
                description = "virtually tied on result log loss"
            else:
                description = ("Matrix has lower" if difference < 0 else "Hybrid has lower") + " result log loss"
            st.caption(
                f"Result log loss difference (Matrix minus Hybrid): {difference:+.4f}; "
                f"{description}. Matrix was lower in "
                f"{row['Matrix lower-loss seasons']} of {row['Seasons']} seasons."
            )
        st.caption(
            "Matrix remains experimental. Small retrospective differences do not "
            "establish future superiority or statistical significance. "
            "Winner-aligned W-H-W scores have not been backtested as a separate method."
        )
        st.caption(
            "Probability calibration and selection thresholds require dated, match-level "
            "pre-match probabilities paired with subsequently settled results. "
            "Aggregate seasonal metrics cannot supply those measurements."
        )
