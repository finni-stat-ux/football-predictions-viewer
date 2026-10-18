"""Historical results must use actually saved, strictly pre-game predictions."""
from pathlib import Path

import pandas as pd
import pytest

from historical_matches import validated_history, competition_label, model_label

ROOT = Path(__file__).resolve().parents[1]


def original_archive():
    return pd.read_csv(ROOT / "published" / "historical_match_results.csv")


def test_published_archive_contains_only_verified_15_oct_pre_match_forecasts():
    actual = validated_history(original_archive())
    assert len(actual) == 51
    assert len(actual[["date", "competition", "HomeTeam", "AwayTeam"]].drop_duplicates()) == 17
    assert actual.model.value_counts().to_dict() == {
        "Hybrid": 17, "Dixon-Coles": 17, "XGBoost": 17
    }
    assert actual.competition.value_counts().to_dict() == {
        "Championship": 36, "EPL": 15
    }
    assert set(actual.forecast_commit) == {
        "615b3c2b9c2cbda33f2507ddca5e617a34d5a2fb"
    }
    assert set(actual.forecast_published_at_utc) == {
        "2026-10-15T11:24:57+00:00"
    }
    burnley = actual[(actual.HomeTeam == "Burnley") & (actual.model == "Hybrid")].iloc[0]
    assert burnley.AwayTeam == "Wolves"
    assert burnley.actual_home_goals == 1 and burnley.actual_away_goals == 2
    assert burnley.p_home_win == pytest.approx(0.47043520)
    assert burnley.pick == "H"
    assert bool(burnley.correct_pick) is False
    brentford = actual[(actual.HomeTeam == "Brentford") & (actual.model == "Hybrid")].iloc[0]
    assert brentford.AwayTeam == "Liverpool"
    assert brentford.actual_home_goals == 1 and brentford.actual_away_goals == 2
    assert brentford.pick == "A"
    assert bool(brentford.correct_pick) is True


@pytest.mark.parametrize("column,value,part", [
    ("forecast_published_at_utc", "2026-10-16T00:00:01+00:00", "strictly before"),
    ("forecast_commit", "not-a-source-commit", "immutable"),
    ("actual_home_goals", -1, "nonnegative"),
    ("actual_away_goals", 1.5, "nonnegative"),
    ("p_home_win", 0.99, "sum to one"),
    ("p_draw", -0.3, "probability"),
    ("most_likely_score", "unavailable", "scoreline"),
    ("result_source_url", "http://example.com/fake", "HTTPS"),
    ("competition", "Fake league", "Unrecognized"),
])
def test_invalid_or_post_match_forecast_never_scores(column, value, part):
    archive = original_archive()
    archive.loc[0, column] = value
    with pytest.raises(ValueError, match=part):
        validated_history(archive)


def test_conflicting_results_or_duplicate_predictions_are_rejected():
    archive = original_archive()
    duplicate = pd.concat([archive, archive.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate historical forecast"):
        validated_history(duplicate)
    conflicting = archive.copy()
    match = conflicting.iloc[0]
    same_match = (
        (conflicting.date == match.date) &
        (conflicting.competition == match.competition) &
        (conflicting.HomeTeam == match.HomeTeam) &
        (conflicting.AwayTeam == match.AwayTeam)
    )
    another = conflicting.index[same_match].tolist()[1]
    conflicting.loc[another, "actual_home_goals"] = 7
    with pytest.raises(ValueError, match="Conflicting final results"):
        validated_history(conflicting)


def test_empty_archive_remains_unavailable_not_fabricated():
    assert validated_history(pd.DataFrame()).empty


def test_streamlit_shows_completed_match_filters_and_source_links():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "viewer_dashboard.py"), default_timeout=60).run()
    assert not app.exception
    labels = [s.label for s in app.selectbox]
    assert "Historical competition" in labels
    assert "Historical model" in labels
    assert "Historical match date" in labels
    assert "Completed match" in labels
    competition = next(s for s in app.selectbox if s.label == "Historical competition")
    competition.select("EPL").run()
    assert not app.exception
    selected = next(s for s in app.selectbox if s.label == "Completed match")
    target = "2026-10-17 · Brentford vs Liverpool"
    assert target in selected.options
    selected.select(target).run()
    assert not app.exception
    assert any("Brentford 1–2 Liverpool" in str(t.value) for t in app.markdown)
    assert any("Original saved forecast" in str(t.value) for t in app.markdown)
    results = [df.value for df in app.dataframe if "Actual FT" in df.value.columns]
    assert len(results) == 1
    assert len(results[0]) == 5
    assert "1-2" in results[0]["Actual FT"].tolist()


def test_historical_filter_names_match_main_viewer():
    """Keep familiar display labels while preserving raw model and league IDs."""
    assert competition_label("EPL") == "English Premier League"
    assert competition_label("Championship") == "EFL Championship"
    assert competition_label("All competitions") == "All competitions"
    assert model_label("Hybrid") == "Hybrid"
    assert model_label("Dixon-Coles") == "Dixon-Coles"
    assert model_label("XGBoost") == "XGBoost"
    assert model_label("Matrix") == "Matrix — Experimental"
    from pathlib import Path
    main = (Path(__file__).resolve().parents[1] / "viewer_dashboard.py").read_text()
    assert "'EPL': 'English Premier League'" in main
    assert "'Championship': 'EFL Championship'" in main
    assert "'Matrix — Experimental' if name == 'Matrix'" in main


def test_historical_dropdowns_apply_consistent_formatters_without_changing_filters():
    from pathlib import Path
    helper = (Path(__file__).resolve().parents[1] / "historical_matches.py").read_text()
    assert "format_func=competition_label" in helper
    assert "format_func=model_label" in helper
    assert '"Historical competition"' in helper
    assert '"Historical model"' in helper
