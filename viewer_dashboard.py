"""Read-only forecasts and historical player form from published snapshots."""
import base64
import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from cloud_refresh_ui import show_cloud_refresh
from viewer_display import (display_table, fixture_player_form, player_panel_html,
                            prediction_card_html, score_chart_svg, score_table_html)

ROOT = Path(__file__).resolve().parent
PUB = ROOT / 'published'
TEAM_LOGOS = json.loads((ROOT / 'assets/team_logos.json').read_text())
COMPETITIONS = {'EPL': 'English Premier League', 'Championship': 'EFL Championship'}
COMPETITION_ASSETS = {'EPL': 'premier-league.png', 'Championship': 'championship.png'}

st.set_page_config(page_title='Conquerors Venture Predictions', layout='wide')
st.markdown((ROOT / 'assets/viewer.css').read_text(), unsafe_allow_html=True)
st.title('Conquerors Venture Predictions')
st.markdown('<p class="cv-intro">Your match forecast. The probabilities behind it.</p>', unsafe_allow_html=True)


@st.cache_data(ttl=60)
def read(name):
    path = PUB / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data(ttl=60)
def read_player_form():
    path = PUB / 'player_form.json'
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except (ValueError, OSError):
        return {}


predictions = read('predictions.csv')
scores = read('top_scores.csv')
metrics = read('model_performance.csv')
if predictions.empty:
    st.info('No predictions published yet.'); st.stop()

st.caption('Predictions updated (UTC): ' + pd.Timestamp(predictions.published_at_utc.iloc[0]).strftime('%d %b %Y, %H:%M UTC'))
league = st.selectbox('Competition', sorted(predictions.competition.unique()), format_func=lambda value: COMPETITIONS.get(value, value))
asset = ROOT / 'assets' / COMPETITION_ASSETS.get(league, '')
logo = ''
if asset.is_file():
    encoded = base64.b64encode(asset.read_bytes()).decode('ascii')
    logo = f'<img src="data:image/png;base64,{encoded}" alt="{escape(COMPETITIONS.get(league, league))} logo">'
st.markdown(f'<div class="cv-league">{logo}<div><h2>{escape(COMPETITIONS.get(league, league))}</h2><p>Full-time result after 90 minutes</p></div></div>', unsafe_allow_html=True)

filtered = predictions[predictions.competition == league]
options = filtered[['fixture_id', 'date', 'HomeTeam', 'AwayTeam']].drop_duplicates()
labels = {r.fixture_id: f'{r.date} · {r.HomeTeam} vs {r.AwayTeam}' for _, r in options.iterrows()}
chosen = st.selectbox('Fixture', options.fixture_id.tolist(), format_func=lambda key: labels[key])
view = filtered[filtered.fixture_id == chosen]
fixture = view.iloc[0]
st.subheader(f'{fixture.HomeTeam} vs {fixture.AwayTeam}')
hybrid = view[view.model == 'Hybrid']
if len(hybrid) == 1:
    try:
        st.markdown(prediction_card_html(hybrid.iloc[0], TEAM_LOGOS), unsafe_allow_html=True)
    except ValueError:
        st.info('Match pick unavailable for this fixture.')

st.subheader('Score probabilities')
model = st.selectbox('Prediction model', ['Hybrid', 'Dixon-Coles', 'XGBoost'])
score = scores[(scores.fixture_id == chosen) & (scores.model == model)].sort_values('rank')
if not score.empty:
    st.markdown('<div class="cv-score-grid"><div><div class="cv-chart-desktop">' + score_chart_svg(score) + '</div><div class="cv-chart-mobile">' + score_chart_svg(score, compact=True) + '</div></div><div>' + score_table_html(score) + '</div></div>', unsafe_allow_html=True)

st.subheader('Top 3 players by recent xG')
st.caption('Recorded xG over the latest five completed league matches. Historical form—not predicted match xG or confirmed starters.')
player_snapshot = read_player_form()
player_form = fixture_player_form(player_snapshot, fixture)
st.markdown('<div class="cv-player-grid">' + ''.join(player_panel_html(team, player_form.get(team), TEAM_LOGOS) for team in (fixture.HomeTeam, fixture.AwayTeam)) + '</div>', unsafe_allow_html=True)
if player_form:
    st.caption('Player data checked (UTC): ' + pd.Timestamp(player_snapshot['generated_at_utc']).strftime('%d %b %Y, %H:%M UTC') + ' · Unreported xG is omitted.')

with st.expander('Compare models and goal estimates'):
    columns = ['model', 'p_home_win', 'p_draw', 'p_away_win', 'expected_home_goals', 'expected_away_goals', 'p_over_2_5', 'p_btts', 'most_likely_score']
    st.dataframe(display_table(view[columns]), hide_index=True, use_container_width=True,
                 column_config={name: st.column_config.NumberColumn(format='%.1f%%') for name in ['Home win (%)', 'Draw (%)', 'Away win (%)', 'Over 2.5 goals (%)', 'Both teams score (%)']})

with st.expander('Historical backtest performance'):
    if metrics.empty:
        st.info('Performance snapshot unavailable.')
    else:
        st.caption('Lower log loss and Brier scores are better; higher accuracy is better.')
        st.dataframe(display_table(metrics), hide_index=True, use_container_width=True)

with st.expander('How the predictions work and refresh options'):
    st.write('The production Hybrid combines Dixon–Coles and XGBoost probabilities equally. Player xG cards show historical context and do not change the current model’s predictions.')
    st.latex(r'P_{Hybrid}(h,a)=\frac{1}{2}P_{DC}(h,a)+\frac{1}{2}P_{XGB}(h,a)')
    if st.button('Refresh displayed predictions', help='Reload the latest published snapshot; does not retrain models'):
        st.cache_data.clear(); st.rerun()
    show_cloud_refresh()

st.caption('Probabilities are estimates, not guarantees. Forecasts and historical player form can become stale; lineups and player availability are not confirmed.')
st.caption('League and team marks identify the competitions covered. All trademarks belong to their owners; no affiliation or endorsement is implied.')
