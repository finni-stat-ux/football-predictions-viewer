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


def show_whw_analysis(fixture_predictions: pd.DataFrame) -> None:
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
    names = [m for m in ("Hybrid", "Matrix", "Dixon-Coles", "XGBoost")
             if m in set(available["model"])]
    source = st.selectbox("Underlying forecast", names, key="whw_source")
    row = available[available["model"] == source].iloc[0]
    st.caption(f"Using {source} probabilities; no W-H-W probabilities are invented.")
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
    score = str(row.get("most_likely_score", "")).strip()
    score_label = score if score and score.lower() not in ("nan", "none") else "Unavailable"
    st.metric("Most likely result", winner)
    st.metric("Most likely score", score_label)
    st.caption(
        "The most likely scoreline is the highest-probability individual score, "
        "so it does not always agree with the most likely overall match result."
    )
    over = float(row["p_over_2_5"])
    btts = float(row["p_btts"])
    records = [
        {"Market": "Match winner", "Prediction": winner,
         "Likelihood": f"{probabilities[pick] * 100:.1f}%"},
        {"Market": "Most likely score", "Prediction": score_label,
         "Likelihood": "See score probabilities"},
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
