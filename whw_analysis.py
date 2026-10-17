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
    records = []
    for label, col in MARKETS:
        p = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
        if pd.notna(p) and math.isfinite(float(p)) and 0 <= float(p) <= 1:
            records.append({"Market": label, "Model probability": float(p)})
    if not records:
        st.warning("No valid probability inputs available.")
        return
    st.dataframe(
        pd.DataFrame(records),
        hide_index=True,
        use_container_width=True,
        column_config={"Model probability": st.column_config.NumberColumn(format="%.1f%%")},
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


def show_whw_formulas() -> None:
    """Display workbook-derived formulas at the bottom of the page."""
    with st.expander("W-H-W Analysis — formulas and interpretation"):
        st.write(
            "W-H-W adapts the uploaded probability/edge backtesting workbook. "
            "It evaluates existing forecasts rather than producing a new "
            "goal-scoring distribution."
        )
        st.markdown("**Implied probability (raw, not margin-adjusted)**")
        st.latex(r"P_{implied} = \\frac{1}{Decimal\\ Odds}")
        st.markdown("**Model probability edge (percentage points)**")
        st.latex(r"Edge = P_{model} - P_{implied}")
        st.markdown("**Binary Brier score for a settled selection**")
        st.latex(r"Brier = (P_{model} - y)^2,\\quad y\\in\\{0,1\\}")
        st.markdown("**Sample-adjusted historical ROI heuristic**")
        st.latex(r"S = ROI \\sqrt{\\frac{\\min(n,100)}{100}}")
        st.caption(
            "n is the number of settled predictions. The sample adjustment "
            "does not prove profitability or statistical significance. "
            "Historical cutoffs must be chosen on past data and tested on "
            "later unseen matches to avoid selection bias."
        )
