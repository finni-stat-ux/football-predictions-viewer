"""W-H-W Analysis: workbook-derived diagnostics, not an independent score model.

The workbook's odds-dependent measures require odds captured at forecast time.
Do not manufacture prices, use future outcomes to rate upcoming matches, or
present retrospective performance as a prediction.
"""
from __future__ import annotations

import math
import pandas as pd
import streamlit as st

MARKETS = (
    ("Home win", "p_home_win"),
    ("Draw", "p_draw"),
    ("Away win", "p_away_win"),
    ("Over 2.5 goals", "p_over_2_5"),
    ("Both teams score", "p_btts"),
)


def implied_probability(decimal_odds: float) -> float:
    """Raw implied probability; includes bookmaker margin."""
    if not math.isfinite(decimal_odds) or decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1.")
    return 1.0 / decimal_odds


def probability_edge(model_probability: float, decimal_odds: float) -> float:
    if not math.isfinite(model_probability) or not 0 <= model_probability <= 1:
        raise ValueError("Model probability must be between 0 and 1.")
    return model_probability - implied_probability(decimal_odds)


def brier_score(probability: float, actual: int) -> float:
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Probability must be between 0 and 1.")
    if actual not in (0, 1):
        raise ValueError("Actual outcome must be 0 or 1.")
    return (probability - actual) ** 2


def sample_adjusted_roi(roi: float, settled_count: int) -> float:
    """Workbook's robustness heuristic; not a statistical confidence interval."""
    if not math.isfinite(roi) or settled_count < 0:
        raise ValueError("ROI must be finite and count nonnegative.")
    return roi * math.sqrt(min(settled_count, 100) / 100)


def scoreline_for_pick(fixture_scores: pd.DataFrame | None, source: str, pick: str) -> tuple[str, float | None]:
    """Find highest-probability *published* score consistent with a 1X2 pick.

    The exported top_scores snapshot contains only five leading scorelines.
    If none fits the pick, show unavailable instead of inventing a score.
    The returned probability is unconditional P(exact score), not P(score | pick).
    """
    if fixture_scores is None or fixture_scores.empty:
        return "Unavailable", None
    if not {"model", "score", "probability"}.issubset(fixture_scores.columns):
        return "Unavailable", None
    if pick not in ("Home win", "Draw", "Away win"):
        raise ValueError("Unknown match result pick")
    candidates = []
    for _, item in fixture_scores[fixture_scores["model"] == source].iterrows():
        parts = str(item["score"]).strip().split("-")
        if len(parts) != 2 or not all(part.isdecimal() for part in parts):
            continue
        home_goals, away_goals = map(int, parts)
        consistent = (
            home_goals > away_goals if pick == "Home win"
            else home_goals < away_goals if pick == "Away win"
            else home_goals == away_goals
        )
        if not consistent:
            continue
        probability = pd.to_numeric(item["probability"], errors="coerce")
        if pd.notna(probability) and math.isfinite(float(probability)) and 0 <= float(probability) <= 1:
            candidates.append((f"{home_goals}-{away_goals}", float(probability)))
    return max(candidates, key=lambda value: value[1]) if candidates else ("Unavailable", None)


def show_whw_analysis(fixture_predictions: pd.DataFrame, fixture_scores: pd.DataFrame | None = None) -> None:
    """Show analysis of published probabilities without changing model forecasts."""
    st.subheader("W-H-W Analysis")
    st.caption(
        "Experimental probability analysis using the existing published model "
        "forecasts. W-H-W does not independently predict scores or change the "
        "underlying probabilities."
    )
    available = fixture_predictions[
        fixture_predictions["model"].isin(("Hybrid", "Matrix", "Dixon-Coles", "XGBoost"))
    ]
    if available.empty:
        st.info("No underlying model forecast is available for W-H-W Analysis.")
        return
    # Keep W-H-W a single-selection, mobile-friendly analysis of the established
    # Hybrid forecast. Never silently switch to another model.
    source = "Hybrid"
    hybrid = available[available["model"] == source]
    if hybrid.empty:
        st.info("W-H-W Analysis needs a published Hybrid forecast for this fixture.")
        return
    row = hybrid.iloc[0]
    st.caption("Based on the published Hybrid forecast; W-H-W does not create new probabilities.")
    st.caption("W-H-W display revision: 18 Oct 2026 · winner-aligned score")
    home = str(row["HomeTeam"])
    away = str(row["AwayTeam"])
    probabilities = {
        "Home win": float(row["p_home_win"]),
        "Draw": float(row["p_draw"]),
        "Away win": float(row["p_away_win"]),
    }
    if not all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values()):
        st.warning("Valid match-result probabilities are unavailable.")
        return
    pick = max(probabilities, key=probabilities.get)
    winner = home if pick == "Home win" else away if pick == "Away win" else "Draw"
    score_label, score_probability = scoreline_for_pick(fixture_scores, source, pick)
    over = float(row["p_over_2_5"])
    btts = float(row["p_btts"])
    records = [
        {"Market": "Match winner", "Prediction": winner,
         "Likelihood": f"{probabilities[pick] * 100:.1f}%"},
        {"Market": "Likely score for pick", "Prediction": score_label,
         "Likelihood": f"{score_probability * 100:.1f}%" if score_probability is not None else "Unavailable"},
    ]
    if math.isfinite(over) and 0 <= over <= 1:
        records.append({
            "Market": "Total goals",
            "Prediction": "Over 2.5 goals" if over >= 0.5 else "Under 2.5 goals",
            "Likelihood": f"{(max(over, 1 - over)) * 100:.1f}%",
        })
    if math.isfinite(btts) and 0 <= btts <= 1:
        records.append({
            "Market": "Both teams to score",
            "Prediction": "Yes" if btts >= 0.5 else "No",
            "Likelihood": f"{(max(btts, 1 - btts)) * 100:.1f}%",
        })
    st.dataframe(pd.DataFrame(records), hide_index=True, use_container_width=True)
    st.caption(
        "Score shown is the most probable of the five published scorelines "
        "consistent with the selected winner or draw. Exact-score likelihood "
        "is unconditional; it is not the chance of that score given a win."
    )
    st.write(
        "The workbook also calculates an odds-based probability edge. "
        "This requires a genuine decimal price recorded at the same time "
        "as the prediction. No odds feed is connected, so an edge is not "
        "shown automatically."
    )
    st.caption(
        "Brier scores require completed outcomes; ROI and sample-adjusted "
        "scores require settled historical observations. They cannot be "
        "calculated for an upcoming fixture from its probabilities alone."
    )



def hybrid_history_rows(metrics: pd.DataFrame) -> pd.DataFrame:
    """Existing chronological Hybrid backtest, not a separate W-H-W backtest."""
    columns = ["Season", "Matches", "Result accuracy", "1X2 log loss", "1X2 Brier"]
    needed = {"season", "model", "matches", "1x2_accuracy", "1x2_log_loss", "1x2_brier"}
    if metrics is None or metrics.empty or not needed.issubset(metrics.columns):
        return pd.DataFrame(columns=columns)
    rows = []
    filtered = metrics[metrics["model"] == "Hybrid"].sort_values("season")
    for _, item in filtered.iterrows():
        try:
            matches = int(item["matches"])
            accuracy = float(item["1x2_accuracy"])
            loss = float(item["1x2_log_loss"])
            brier = float(item["1x2_brier"])
        except (ValueError, TypeError, OverflowError):
            continue
        if not (matches > 0 and 0 <= accuracy <= 1 and all(
            math.isfinite(v) and v >= 0 for v in (loss, brier)
        )):
            continue
        rows.append({
            "Season": str(item["season"]).replace("_", "/"),
            "Matches": matches,
            "Result accuracy": f"{accuracy * 100:.1f}%",
            "1X2 log loss": f"{loss:.4f}",
            "1X2 Brier": f"{brier:.4f}",
        })
    return pd.DataFrame(rows, columns=columns)


def show_whw_history(metrics: pd.DataFrame) -> None:
    """Expose grounded historical model reliability without inventing W-H-W ROI."""
    with st.expander("W-H-W historical evidence · Hybrid (both leagues)"):
        history = hybrid_history_rows(metrics)
        if history.empty:
            st.info("Historical Hybrid performance data is not available.")
            return
        recent = history.iloc[-1]
        st.caption(
            f"Latest available season {recent['Season']}: "
            f"{recent['Result accuracy']} match-result accuracy over "
            f"{recent['Matches']:,} completed matches."
        )
        st.dataframe(history, hide_index=True, use_container_width=True)
        st.caption(
            "Existing historical backtests for the underlying Hybrid, across "
            "English Premier League and Championship combined—not a separately "
            "measured W-H-W model or live prediction record. Lower log loss and "
            "1X2 Brier are better. This 1X2 Brier is multiclass, whereas the "
            "uploaded workbook's selection Brier is binary."
        )
        st.caption(
            "The winner-aligned score displayed by W-H-W has not been "
            "independently backtested. No bookmaker odds or settled selection "
            "history is available to establish edge or ROI."
        )


def show_whw_formulas() -> None:
    """Display workbook-derived formulas at the bottom of the page."""
    with st.expander("W-H-W Analysis — formulas and interpretation"):
        st.write(
            "W-H-W adapts the uploaded probability/edge backtesting workbook. "
            "It evaluates existing forecasts rather than producing a new "
            "goal-scoring distribution."
        )
        st.markdown("**Implied probability (raw, not margin-adjusted)**")
        st.latex(r"P_{implied} = \frac{1}{Decimal\ Odds}")
        st.markdown("**Model probability edge (percentage points)**")
        st.latex(r"Edge = P_{model} - P_{implied}")
        st.markdown("**Binary Brier score for a settled selection**")
        st.latex(r"Brier = (P_{model} - y)^2,\quad y\in\{0,1\}")
        st.markdown("**Sample-adjusted historical ROI heuristic**")
        st.latex(r"S = ROI \sqrt{\frac{\min(n,100)}{100}}")
        st.caption(
            "n is the number of settled predictions. The sample adjustment "
            "does not prove profitability or statistical significance. "
            "Historical cutoffs must be chosen on past data and tested on "
            "later unseen matches to avoid selection bias."
        )
