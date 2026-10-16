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

def score_chart_svg(scores, compact=False):
    """Static SVG: deliberately has no zoom, resize handles or fullscreen control."""
    from html import escape
    items = [(str(r['score']), float(r['probability']) * 100) for _, r in scores.iterrows()]
    if not items:
        return ''
    width, height, left, bottom = (360 if compact else 640), 300, 48, 250
    maximum = max(5, math.ceil(max(v for _, v in items) / 5) * 5)
    plot_width = width - left - 16
    step = plot_width / len(items)
    marks = []
    for tick in range(5):
        value = maximum * tick / 4
        y = bottom - value / maximum * 210
        marks.append(f'<line x1="{left}" x2="{width-16}" y1="{y}" y2="{y}" stroke="currentColor" opacity=".15"/><text x="40" y="{y+4}" text-anchor="end" fill="currentColor" font-size="12">{value:g}%</text>')
    for i, (label, value) in enumerate(items):
        x = left + i * step + step * .15
        bar_height = value / maximum * 210
        marks.append(f'<rect x="{x}" y="{bottom-bar_height}" width="{step*.7}" height="{bar_height}" rx="4" fill="#7856d8"/><text x="{x+step*.35}" y="{bottom+22}" text-anchor="middle" fill="currentColor" font-size="12">{escape(label)}</text><text x="{x+step*.35}" y="{bottom-bar_height-7}" text-anchor="middle" fill="currentColor" font-size="12">{value:.1f}%</text>')
    return f'<svg role="img" aria-label="Score probabilities, static chart" viewBox="0 0 {width} 300" style="display:block;width:100%;height:300px;pointer-events:none" xmlns="http://www.w3.org/2000/svg"><title>Score probabilities</title>' + ''.join(marks) + '</svg>'


def team_badge(team, logos, size=36):
    from html import escape
    url = logos.get(team, '')
    if not url.startswith('https://a.espncdn.com/'):
        return ''
    return f'<img src="{escape(url, quote=True)}" alt="{escape(team, quote=True)} crest" width="{size}" height="{size}" style="object-fit:contain;background:white;border-radius:6px;padding:4px;vertical-align:middle;flex-shrink:0">'


def winner_team(row):
    pick, _ = match_pick(row)
    for team in (row['HomeTeam'], row['AwayTeam']):
        if pick == f'{team} to win':
            return team
    return None

def score_table_html(scores):
    """Exactly one row per score, without dataframe filler rows or controls."""
    from html import escape
    rows = ''.join(f'<tr><td>{int(r["rank"])}</td><td>{escape(str(r["score"]))}</td><td>{float(r["probability"]):.1%}</td></tr>' for _, r in scores.iterrows())
    return '<table class="cv-score-table" aria-label="Exact score probabilities"><thead><tr><th scope="col">Rank</th><th scope="col">Score</th><th scope="col">Probability</th></tr></thead><tbody>' + rows + '</tbody></table>'


def fixture_player_form(snapshot, fixture, now=None):
    """Reject data from a different fixture or stale source after refresh."""
    import pandas as pd
    if snapshot.get('schema_version') != 1:
        return {}
    record = snapshot.get('fixtures', {}).get(str(fixture['fixture_id']), {})
    expected = {'date': str(pd.Timestamp(fixture['date']).date()), 'competition': fixture['competition'], 'HomeTeam': fixture['HomeTeam'], 'AwayTeam': fixture['AwayTeam']}
    if any(record.get(k) != value for k, value in expected.items()):
        return {}
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    now = now.tz_localize('UTC') if now.tzinfo is None else now.tz_convert('UTC')
    try:
        generated = pd.Timestamp(snapshot['generated_at_utc'])
        generated = generated.tz_localize('UTC') if generated.tzinfo is None else generated.tz_convert('UTC')
        if generated > now:
            return {}
        teams = {}
        for name, info in record.get('teams', {}).items():
            if info.get('status') != 'available':
                continue
            source = pd.Timestamp(info['source_through'], tz='UTC')
            age = (now.normalize() - source).days
            if 0 <= age <= snapshot.get('max_age_days', 45) and source < pd.Timestamp(expected['date'], tz='UTC'):
                teams[name] = info
        return teams
    except (KeyError, ValueError, TypeError):
        return {}


def prediction_card_html(row, logos):
    from html import escape
    pick, probability = match_pick(row)
    winner = winner_team(row)
    badge = team_badge(winner, logos, 48) if winner else ''
    cells=[]
    for key, team, label in zip(OUTCOMES, (row['HomeTeam'], None, row['AwayTeam']), (f"{row['HomeTeam']} win", 'Draw', f"{row['AwayTeam']} win")):
        logo = team_badge(team, logos, 32) if team else ''
        cells.append(f'<div class="cv-outcome"><div class="cv-outcome-label">{logo}<span>{escape(label)}</span></div><strong>{float(row[key]):.1%}</strong></div>')
    return f'<section class="cv-pick" aria-label="Hybrid match pick"><div class="cv-eyebrow">HYBRID MATCH PICK</div><div class="cv-pick-title">{badge}<h3>{escape(pick)}</h3></div><p class="cv-pick-probability">{probability:.1%} estimated probability</p><p class="cv-note">Most likely single result · 90 minutes · Other outcomes remain possible.</p><div class="cv-outcomes">'+''.join(cells)+'</div></section>'


def player_panel_html(team, info, logos):
    from html import escape
    header = f'<div class="cv-player-heading">{team_badge(team, logos)}<span>{escape(team)}</span></div>'
    if not info:
        content = '<p class="cv-note">Recent player xG is not yet available. Older seasons are not shown as current form.</p>'
    else:
        content = f'<p class="cv-note">Five league matches · {escape(info["source_from"])} to {escape(info["source_through"])}</p><ol class="cv-player-list">'
        for index, player in enumerate(info['players'][:3], 1):
            content += f'<li><div><span class="cv-name">{index}. {escape(player["name"])}</span><small>{int(player["minutes"])} minutes · {int(player["appearances"])} appearances</small></div><div class="cv-player-xg">{float(player["xg"]):.2f}<small>recorded xG</small></div></li>'
        content += '</ol>'
    return '<section class="cv-player-panel">'+header+content+'</section>'
