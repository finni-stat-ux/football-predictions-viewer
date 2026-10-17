"""Pure-math regression checks for W-H-W Analysis.

Run: python -m unittest discover -s tests -p 'test_whw_analysis.py'
"""
import math
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
