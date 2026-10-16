"""Read-only forecasts and historical player form from published snapshots."""
import base64
import json
import io
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from cloud_refresh_ui import show_cloud_refresh
from matrix_display import load_matrix, performance_summary
from viewer_display import (display_table, fixture_player_form, player_panel_html,
                            prediction_card_html, score_chart_svg, score_table_html, upcoming_fixtures, fixture_tile_label)

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


@st.cache_data(ttl=60)
def read_prediction_snapshot():
    path = PUB / 'predictions.csv'
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}
    content = path.read_bytes()
    original = pd.read_csv(io.BytesIO(content))
    original_scores = pd.read_csv(PUB / 'top_scores.csv')
    original_metrics = pd.read_csv(PUB / 'model_performance.csv')
    matrix_p, matrix_s, matrix_m, metadata = load_matrix(PUB, content)
    return original, original_scores, original_metrics, matrix_p, matrix_s, matrix_m, metadata

predictions, scores, metrics, matrix_predictions, matrix_scores, matrix_metrics, matrix_metadata = read_prediction_snapshot()
if not matrix_predictions.empty:
    predictions = pd.concat([predictions, matrix_predictions], ignore_index=True)
    scores = pd.concat([scores, matrix_scores], ignore_index=True)
if predictions.empty:
    st.info('No predictions published yet.'); st.stop()

st.caption('Predictions updated (UTC): ' + pd.Timestamp(predictions.published_at_utc.iloc[0]).strftime('%d %b %Y, %H:%M UTC'))
league = st.selectbox('Competition', sorted(predictions.competition.unique()), format_func=lambda value: COMPETITIONS.get(value, value), filter_mode=None)
asset = ROOT / 'assets' / COMPETITION_ASSETS.get(league, '')
logo = ''
if asset.is_file():
    encoded = base64.b64encode(asset.read_bytes()).decode('ascii')
    logo = f'<img src="data:image/png;base64,{encoded}" alt="{escape(COMPETITIONS.get(league, league))} logo">'
st.markdown(f'<div class="cv-league">{logo}<div><h2>{escape(COMPETITIONS.get(league, league))}</h2><p>Full-time result after 90 minutes</p></div></div>', unsafe_allow_html=True)

filtered = predictions[predictions.competition == league]
@st.cache_data(ttl=60)
def read_schedule():
    path=PUB/'fixture_schedule.json'
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except (ValueError,OSError):
        return {}

options = upcoming_fixtures(filtered, read_schedule())
if options.empty:
    st.info('No upcoming matches in the published snapshot. Refresh the predictions for the next fixtures.'); st.stop()
selection_key = 'selected_fixture_' + league
available = options.fixture_id.tolist()
if st.session_state.get(selection_key) not in available:
    st.session_state[selection_key] = available[0]
chosen = st.session_state[selection_key]

@st.fragment(run_every=60)
def keep_upcoming_current():
    if upcoming_fixtures(filtered, read_schedule()).fixture_id.tolist() != available:
        st.rerun(scope='app')

keep_upcoming_current()

def choose_fixture(key, fixture_id):
    st.session_state[key] = fixture_id

st.subheader('Choose an upcoming match')
st.caption('Tap a match tile. Swipe or scroll sideways for more matches. Kickoff times are shown in Sydney time.')
with st.container(horizontal=True, wrap=False, key='fixture_tiles'):
    for _, match in options.iterrows():
        st.button(fixture_tile_label(match, TEAM_LOGOS), key='fixture_tile_' + str(match.fixture_id), width=260,
                  type='primary' if match.fixture_id == chosen else 'secondary',
                  on_click=choose_fixture, args=(selection_key, match.fixture_id),
                  help=f"{match.HomeTeam} vs {match.AwayTeam} · {match.display_time}")
view = filtered[filtered.fixture_id == chosen]
fixture = view.iloc[0]
st.subheader(f'{fixture.HomeTeam} vs {fixture.AwayTeam}')
model_options = [name for name in ['Hybrid', 'Dixon-Coles', 'XGBoost', 'Matrix'] if name in view.model.values]
model = st.selectbox('Prediction model', model_options,
                     format_func=lambda name: 'Matrix — Experimental' if name == 'Matrix' else name,
                     filter_mode=None)
selected_prediction = view[view.model == model]
if len(selected_prediction) == 1:
    try:
        st.markdown(prediction_card_html(selected_prediction.iloc[0], TEAM_LOGOS), unsafe_allow_html=True)
    except ValueError:
        st.info('Match pick unavailable for this fixture.')
if model == 'Matrix':
    st.caption('Experimental formula · Measured separately · Not proven better than Hybrid. Historical player xG is context, not an input.')
    if matrix_metadata.get('published_at_utc'):
        st.caption('Matrix updated: ' + pd.Timestamp(matrix_metadata['published_at_utc']).strftime('%d %b %Y, %H:%M UTC') + ' · Historical results through ' + matrix_metadata.get('historical_data_through', 'unknown'))

st.subheader('Score probabilities')
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

if not matrix_predictions.empty:
    with st.expander('Matrix performance · ' + COMPETITIONS.get(league, league), expanded=model == 'Matrix'):
        summary = performance_summary(matrix_metrics, league)
        baseline = performance_summary(matrix_metrics, league, 'Hybrid')
        if summary and baseline:
            st.caption(f"Separate retrospective measure · {summary['matches']:,} matches · Chronological season tests, not live accuracy.")
            a, b, c = st.columns(3)
            a.metric('Matrix result log loss ↓', f"{summary['1x2_log_loss']:.4f}")
            b.metric('Matrix Brier score ↓', f"{summary['1x2_brier']:.4f}")
            c.metric('Matrix result accuracy', f"{summary['1x2_accuracy']:.1%}")
            gain = 100 * (1 - summary['1x2_log_loss'] / baseline['1x2_log_loss'])
            direction = 'lower' if gain >= 0 else 'higher'
            st.caption(f"Result log loss is {abs(gain):.2f}% {direction} than Hybrid on the same {COMPETITIONS.get(league, league)} matches. Lower is better; this does not establish future performance.")
            shown = matrix_metrics[matrix_metrics.competition == league].drop(columns=['competition'])
            st.dataframe(display_table(shown), hide_index=True, use_container_width=True)

with st.expander('Historical backtest performance'):
    if metrics.empty:
        st.info('Performance snapshot unavailable.')
    else:
        st.caption('Lower log loss and Brier scores are better; higher accuracy is better.')
        st.dataframe(display_table(metrics), hide_index=True, use_container_width=True)

with st.expander('How the predictions work and refresh options'):
    st.write('The production Hybrid combines Dixon–Coles and XGBoost probabilities equally. Player xG cards show historical context and do not change the current model’s predictions.')
    st.latex(r'P_{Hybrid}(h,a)=\frac{1}{2}P_{DC}(h,a)+\frac{1}{2}P_{XGB}(h,a)')
    if not matrix_predictions.empty:
        st.write('Matrix is a separate experimental formula. It combines Dixon–Coles, an Elo-enhanced XGBoost model and a direct home/draw/away logistic model. Each league has its own weights learned from earlier out-of-fold seasons. Its score grid is adjusted to agree with its result probabilities.')
        st.latex(r'P_{Matrix}(r)=w_{DC}P_{DC}(r)+w_{XGB}P_{XGB+Elo}(r)+w_{LR}P_{LR}(r)')
        weights = matrix_metadata.get('weights', {}).get(league, {})
        if weights:
            st.caption('Current ' + COMPETITIONS.get(league, league) + ' Matrix weights: ' + ' · '.join(f'{name} {value:.1%}' for name, value in weights.items()))
    if st.button('Refresh displayed predictions', help='Reload the latest published snapshot; does not retrain models'):
        st.cache_data.clear(); st.rerun()
    show_cloud_refresh()

st.caption('Probabilities are estimates, not guarantees. Forecasts and historical player form can become stale; lineups and player availability are not confirmed.')
st.caption('League and team marks identify the competitions covered. All trademarks belong to their owners; no affiliation or endorsement is implied.')
