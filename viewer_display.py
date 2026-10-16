"""Presentation helpers; published probabilities are never changed."""
import math

OUTCOMES = ('p_home_win', 'p_draw', 'p_away_win')
PROBABILITY_COLUMNS = (*OUTCOMES, 'p_over_2_5', 'p_btts')
LABELS = {
    'model': 'Model', 'p_home_win': 'Home win (%)', 'p_draw': 'Draw (%)',
    'p_away_win': 'Away win (%)', 'expected_home_goals': 'Home expected goals',
    'expected_away_goals': 'Away expected goals', 'p_over_2_5': 'Over 2.5 goals (%)',
    'p_btts': 'Both teams score (%)', 'most_likely_score': 'Most likely score',
    'rank': 'Rank', 'score': 'Score', 'probability': 'Probability (%)',
    'season': 'Season', 'matches': 'Matches', '1x2_log_loss': 'Result log loss ↓',
    '1x2_brier': 'Result Brier score ↓', '1x2_accuracy': 'Result accuracy (%)',
    'exact_score_hit_rate': 'Exact score accuracy (%)',
    'exact_score_log_loss': 'Exact score log loss ↓', 'goals_over_cap': 'Scores beyond goal cap',
}

def match_pick(row):
    values = [float(row[c]) for c in OUTCOMES]
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in values) or not math.isclose(sum(values), 1, abs_tol=1e-5):
        raise ValueError('Invalid outcome probabilities')
    best = max(values)
    winners = [i for i, v in enumerate(values) if math.isclose(v, best, abs_tol=1e-8, rel_tol=0)]
    if len(winners) != 1:
        return 'Too close to call', best
    labels = (f"{row['HomeTeam']} to win", 'Draw', f"{row['AwayTeam']} to win")
    return labels[winners[0]], best

def display_table(frame):
    result = frame.copy()
    for name in (*PROBABILITY_COLUMNS, 'probability', '1x2_accuracy', 'exact_score_hit_rate'):
        if name in result:
            result[name] = result[name] * 100
    return result.rename(columns=LABELS)
