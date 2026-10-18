"""Regression checks for matched historical model comparisons."""
from pathlib import Path

import pandas as pd
import pytest

from model_accuracy import compare_leagues, paired_season_metrics


def sample_metrics():
    rows = []
    for league, n in (("EPL", 380), ("Championship", 552)):
        for season, offset in (("2023_24", 0), ("2024_25", 0.01)):
            rows += [
                {"competition": league, "season": season, "model": "Hybrid",
                 "matches": n, "1x2_log_loss": 1.0 + offset,
                 "1x2_brier": 0.60, "1x2_accuracy": 0.50,
                 "exact_score_log_loss": 2.85, "exact_score_hit_rate": 0.11},
                {"competition": league, "season": season, "model": "Matrix",
                 "matches": n, "1x2_log_loss": 0.99 + offset,
                 "1x2_brier": 0.59, "1x2_accuracy": 0.51,
                 "exact_score_log_loss": 2.83, "exact_score_hit_rate": 0.12},
            ]
    return pd.DataFrame(rows)


def test_matched_comparison_respects_competition_and_weights():
    frame = compare_leagues(sample_metrics())
    assert len(frame) == 2
    assert frame["Matches"].tolist() == [760, 1104]
    assert frame["Seasons"].tolist() == [2, 2]
    assert (frame["Matrix lower-loss seasons"] == 2).all()
    assert all(value == pytest.approx(-0.01) for value in frame["Log loss difference"])


def test_unpaired_or_invalid_rows_are_not_mixed():
    raw = sample_metrics()
    raw = raw.loc[~((raw.competition == "EPL") & (raw.season == "2024_25") &
                    (raw.model == "Matrix"))].copy()
    raw.loc[(raw.competition == "Championship") & (raw.model == "Matrix"), "matches"] += 1
    paired = paired_season_metrics(raw)
    assert len(paired) == 2
    assert set(paired.competition) == {"EPL"}
    assert set(paired.season) == {"2023_24"}


def test_empty_and_duplicate_samples_safely_omit_comparison():
    assert compare_leagues(pd.DataFrame()).empty
    duplicated = pd.concat([sample_metrics(), sample_metrics().iloc[[0]]], ignore_index=True)
    assert compare_leagues(duplicated).empty


def test_published_matrix_and_hybrid_have_matching_season_samples():
    root = Path(__file__).resolve().parents[1]
    raw = pd.read_csv(root / "published" / "matrix_performance.csv")
    paired = paired_season_metrics(raw)
    summary = compare_leagues(raw)
    assert len(paired) == 12
    assert summary["Matches"].tolist() == [1140, 1656]
    assert summary.iloc[0]["Log loss difference"] == pytest.approx(0.0000957935, abs=1e-7)
    assert summary.iloc[1]["Log loss difference"] == pytest.approx(-0.0052712995, abs=1e-7)
