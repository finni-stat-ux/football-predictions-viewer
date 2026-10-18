"""Age calculation for published forecasts (not website deployment date).

A code deployment must not be described as a data/model refresh.
"""
from __future__ import annotations

import math
import pandas as pd


def hours_since_forecast(published_at_utc, now_utc=None) -> float | None:
    """Return non-negative elapsed hours; None for invalid timestamps."""
    timestamp = pd.to_datetime(published_at_utc, utc=True, errors="coerce")
    reference = (
        pd.Timestamp.now(tz="UTC")
        if now_utc is None
        else pd.to_datetime(now_utc, utc=True, errors="coerce")
    )
    if pd.isna(timestamp) or pd.isna(reference):
        return None
    age = (reference - timestamp).total_seconds() / 3600
    return max(0.0, age) if math.isfinite(age) else None


def stale_forecast_notice(published_at_utc, now_utc=None, limit_hours=48) -> str | None:
    """User-facing warning when snapshot is older than the threshold."""
    age_hours = hours_since_forecast(published_at_utc, now_utc)
    if age_hours is None:
        return "Forecast age cannot be verified. Check the latest prediction refresh."
    if age_hours < limit_hours:
        return None
    days = int(age_hours // 24)
    age_label = f"{days} day{'s' if days != 1 else ''}" if days else f"{int(age_hours)} hours"
    return (
        f"Predictions were generated {age_label} ago. Recent results may not "
        "be included. Use 'Cloud Prediction Refresh' under 'How the "
        "predictions work and refresh options' to retrain and republish; "
        "'Refresh displayed predictions' only reloads the current snapshot."
    )
