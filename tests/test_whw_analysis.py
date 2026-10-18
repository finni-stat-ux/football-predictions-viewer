"""Pure-math regression checks for W-H-W Analysis.

Run: python -m unittest discover -s tests -p 'test_whw_analysis.py'
"""
import math
import pandas as pd
import sys
import types
import unittest

# The formula functions do not require a running Streamlit session.
try:
    import streamlit  # noqa: F401
except ImportError:
    sys.modules["streamlit"] = types.ModuleType("streamlit")

from whw_analysis import (
    implied_probability,
    probability_edge,
    brier_score,
    sample_adjusted_roi,
    scoreline_for_pick,
)


class WHWFormulaTests(unittest.TestCase):
    def test_implied_probability(self):
        self.assertAlmostEqual(implied_probability(2.5), 0.4)

    def test_probability_edge(self):
        self.assertAlmostEqual(probability_edge(0.55, 2.5), 0.15)

    def test_brier_score(self):
        self.assertAlmostEqual(brier_score(0.8, 1), 0.04)
        self.assertAlmostEqual(brier_score(0.8, 0), 0.64)

    def test_sample_adjusted_roi(self):
        self.assertAlmostEqual(sample_adjusted_roi(0.12, 25), 0.06)
        self.assertAlmostEqual(sample_adjusted_roi(0.12, 100), 0.12)
        self.assertAlmostEqual(sample_adjusted_roi(0.12, 200), 0.12)
        self.assertEqual(sample_adjusted_roi(0.12, 0), 0)

    def test_scoreline_matches_result(self):
        scores = pd.DataFrame([
            {"model": "Hybrid", "score": "1-1", "probability": 0.111},
            {"model": "Hybrid", "score": "1-0", "probability": 0.0962},
            {"model": "Hybrid", "score": "2-1", "probability": 0.0961},
            {"model": "Hybrid", "score": "2-0", "probability": 0.0860},
            {"model": "Hybrid", "score": "0-1", "probability": 0.0619},
            {"model": "XGBoost", "score": "3-0", "probability": 0.99},
        ])
        self.assertEqual(scoreline_for_pick(scores, "Hybrid", "Home win"), ("1-0", 0.0962))
        self.assertEqual(scoreline_for_pick(scores, "Hybrid", "Draw"), ("1-1", 0.111))
        self.assertEqual(scoreline_for_pick(scores, "Hybrid", "Away win"), ("0-1", 0.0619))

    def test_missing_consistent_score_is_not_fabricated(self):
        scores = pd.DataFrame([{"model": "Hybrid", "score": "1-1", "probability": 0.11}])
        self.assertEqual(scoreline_for_pick(scores, "Hybrid", "Home win"), ("Unavailable", None))
        self.assertEqual(scoreline_for_pick(None, "Hybrid", "Draw"), ("Unavailable", None))

    def test_scoreline_invalid_entries_ignored(self):
        scores = pd.DataFrame([
            {"model": "Hybrid", "score": "2-0", "probability": float("nan")},
            {"model": "Hybrid", "score": "bad", "probability": 0.95},
            {"model": "Hybrid", "score": "2-1", "probability": 0.09},
        ])
        self.assertEqual(scoreline_for_pick(scores, "Hybrid", "Home win"), ("2-1", 0.09))

    def test_invalid_odds(self):
        for odds in (0, 1, -3, float("nan"), float("inf")):
            with self.subTest(odds=odds):
                with self.assertRaises(ValueError):
                    implied_probability(odds)

    def test_invalid_probabilities(self):
        for p in (-0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(probability=p):
                with self.assertRaises(ValueError):
                    probability_edge(p, 2.0)
                with self.assertRaises(ValueError):
                    brier_score(p, 1)

    def test_invalid_outcome_and_sample(self):
        with self.assertRaises(ValueError):
            brier_score(0.5, 2)
        with self.assertRaises(ValueError):
            sample_adjusted_roi(0.1, -1)
        with self.assertRaises(ValueError):
            sample_adjusted_roi(math.inf, 10)


if __name__ == "__main__":
    unittest.main()
