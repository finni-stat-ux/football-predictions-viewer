"""Read-only forecasts and historical player form from published snapshots."""
import base64
import json
import io
import importlib
import inspect
import logging
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from cloud_refresh_ui import show_cloud_refresh
from matrix_display import load_matrix, performance_summary
# Streamlit Cloud may cache model_accuracy from before the single-footer update.
# Reload only this stateless display helper; leave authenticated refresh module
# intact so its process-wide login rate limit is never reset by app reruns.
import model_accuracy
model_accuracy = importlib.reload(model_accuracy)
show_league_accuracy = model_accuracy.show_league_accuracy
from viewer_freshness import stale_forecast_notice
# Reload the stateless historical-results helper after Streamlit Cloud updates.
import historical_matches
historical_matches = importlib.reload(historical_matches)
# Streamlit Cloud can keep imported modules in memory after syncing GitHub.
# Reload the lightweight W-H-W module on a viewer rerun so UI changes appear.
import whw_analysis
whw_analysis = importlib.reload(whw_analysis)
show_whw_analysis = whw_analysis.show_whw_analysis
show_whw_formulas = whw_analysis.show_whw_formulas
# Streamlit reruns may retain a stale imported module after a GitHub sync.
# Reload the display helpers so fixture-identity recovery actually reaches the UI.
import viewer_display
viewer_display = importlib.reload(viewer_display)
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

# Sport selection leaves existing football controls and their original indices
# untouched. ATP has its own optional, independently validated forecast files.
from sport_icons import show_sport_picker
sport = show_sport_picker()
if sport == "ATP Men's Singles":
    # Match the existing football reload policy: Cloud may cache imported UI modules.
    import tennis_design, tennis_fixtures_viewer, tennis_viewer, tennis_performance
    importlib.reload(tennis_design)
    importlib.reload(tennis_fixtures_viewer)
    importlib.reload(tennis_performance)
    importlib.reload(tennis_viewer)
    tennis_viewer.show_atp(ROOT)
    st.stop()


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
def read_forecast_metadata():
    path = PUB / 'metadata.json'
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
age_notice = stale_forecast_notice(predictions.published_at_utc.iloc[0])
if age_notice:
    st.warning(age_notice)
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
model_options.append('W-H-W Analysis')
model = st.selectbox('Prediction model', model_options,
                     format_func=lambda name: 'Matrix — Experimental' if name == 'Matrix' else name,
                     filter_mode=None)
selected_prediction = view[view.model == model]
if model == 'W-H-W Analysis':
    try:
        # Pass the score snapshot only if the loaded analysis module supports it.
        # Streamlit Cloud can briefly retain an older imported module across a redeploy.
        import inspect
        parameters = inspect.signature(show_whw_analysis).parameters
        if "fixture_scores" in parameters:
            show_whw_analysis(view, fixture_scores=scores[scores.fixture_id == chosen])
        else:
            show_whw_analysis(view)
    except Exception as exc:
        logging.getLogger(__name__).exception("W-H-W Analysis failed for fixture %s", chosen)
        st.error("W-H-W Analysis encountered an issue. Other prediction models are still available.")
        st.caption(f"Diagnostic: {type(exc).__name__}: {str(exc)[:300]}")
        st.caption("This message identifies the failure without exposing the full server traceback.")
if len(selected_prediction) == 1:
    try:
        st.markdown(prediction_card_html(selected_prediction.iloc[0], TEAM_LOGOS), unsafe_allow_html=True)
    except ValueError:
        st.info('Match pick unavailable for this fixture.')
if model == 'Matrix':
    st.caption('Experimental formula · Measured separately · Not proven better than Hybrid. Historical player xG is context, not an input.')
    if matrix_metadata.get('published_at_utc'):
        st.caption('Matrix updated: ' + pd.Timestamp(matrix_metadata['published_at_utc']).strftime('%d %b %Y, %H:%M UTC') + ' · Historical results through ' + matrix_metadata.get('historical_data_through', 'unknown'))

if model != 'W-H-W Analysis':
    st.subheader('Score probabilities')
    score = scores[(scores.fixture_id == chosen) & (scores.model == model)].sort_values('rank')
    if not score.empty:
        st.markdown('<div class="cv-score-grid"><div><div class="cv-chart-desktop">' + score_chart_svg(score) + '</div><div class="cv-chart-mobile">' + score_chart_svg(score, compact=True) + '</div></div><div>' + score_table_html(score) + '</div></div>', unsafe_allow_html=True)

st.subheader('Top 3 players by recorded xG')
st.caption('Recorded xG from each team\'s last five verified matches at the player-data snapshot date. This historical form may lag behind the latest results—not predicted xG or confirmed starters.')
player_snapshot = read_player_form()
player_form = fixture_player_form(player_snapshot, fixture)
st.markdown('<div class="cv-player-grid">' + ''.join(player_panel_html(team, player_form.get(team), TEAM_LOGOS) for team in (fixture.HomeTeam, fixture.AwayTeam)) + '</div>', unsafe_allow_html=True)
if player_form:
    snapshot_time = pd.Timestamp(player_snapshot['generated_at_utc'])
    st.caption('Player xG snapshot (UTC): ' + snapshot_time.strftime('%d %b %Y, %H:%M UTC') + ' · Data verified through the dates shown for each team.')
    historical_through = read_forecast_metadata().get('historical_data_through')
    if historical_through and pd.Timestamp(historical_through).date() > snapshot_time.date():
        st.caption(
            'Player data predates the latest match results (' + str(historical_through) +
            '). Displayed player rankings are an older verified five-match sample, '
            'not necessarily each team\'s latest five matches.'
        )

# Historical match outcomes are a separate, verified archive, never a replay
# from today's trained model. Selecting a past match cannot alter live picks.
historical_matches.show_historical_matches(read('historical_match_results.csv'), league)

# One compact information centre: no stacked model accordions on mobile.
with st.expander('Models & performance · methods, comparisons and results'):
    tab_methods, tab_comparison, tab_results = st.tabs([
        'Models & formulas', 'Match comparison', 'Historical results'
    ])

    with tab_methods:
        st.markdown('**Dixon–Coles**')
        st.write('Estimates goal-scoring rates from previous results, with an adjustment for low-scoring outcomes.')
        st.markdown('**XGBoost**')
        st.write('Learns expected home and away goals from historical, pre-match team features.')
        st.markdown('**Hybrid · production default**')
        st.write('Blends the Dixon–Coles and XGBoost exact-score probability grids equally. Historical player xG is displayed separately and does not change model predictions.')
        st.latex(r'P_{Hybrid}(h,a)=\frac{1}{2}P_{DC}(h,a)+\frac{1}{2}P_{XGB}(h,a)')
        if not matrix_predictions.empty:
            st.markdown('**Matrix · experimental**')
            st.write('A separately measured blend of Dixon–Coles, Elo-enhanced XGBoost and direct-result logistic probabilities. League-specific weights come from earlier out-of-fold seasons; the score grid is reconciled to match the resulting home/draw/away probabilities.')
            st.latex(r'P_{Matrix}(r)=w_{DC}P_{DC}(r)+w_{XGB}P_{XGB+Elo}(r)+w_{LR}P_{LR}(r)')
            weights = matrix_metadata.get('weights', {}).get(league, {})
            if weights:
                st.caption('Current ' + COMPETITIONS.get(league, league) + ' Matrix weights: ' + ' · '.join(f'{name} {value:.1%}' for name, value in weights.items()))
        st.markdown('**W-H-W Analysis · probability interpretation**')
        st.write('Uses published Hybrid probabilities to present a winner-aligned score from the five highest-ranked scorelines. It does not generate an independent forecast or establish profitability.')
        show_whw_formulas(embedded=True)

    with tab_comparison:
        st.caption('Current selected fixture, with predictions from the available football models.')
        columns = ['model', 'p_home_win', 'p_draw', 'p_away_win', 'expected_home_goals', 'expected_away_goals', 'p_over_2_5', 'p_btts', 'most_likely_score']
        st.dataframe(display_table(view[columns]), hide_index=True, use_container_width=True,
                     column_config={name: st.column_config.NumberColumn(format='%.1f%%') for name in ['Home win (%)', 'Draw (%)', 'Away win (%)', 'Over 2.5 goals (%)', 'Both teams score (%)']})
        st.caption('W-H-W is an analysis of Hybrid, not an independent prediction model.')

    with tab_results:
        st.caption('Historical, retrospectively evaluated forecasts. Lower log loss and Brier scores are better; higher accuracy is better.')
        if not metrics.empty:
            st.markdown('**Production model historical backtests · both leagues**')
            st.dataframe(display_table(metrics), hide_index=True, use_container_width=True)
        else:
            st.info('Production backtest snapshot unavailable.')
        if not matrix_metrics.empty:
            st.markdown('**Hybrid vs Matrix · league-specific matched samples**')
            show_league_accuracy(matrix_metrics, embedded=True)
            st.markdown('**Matrix detailed historical seasons · ' + COMPETITIONS.get(league, league) + '**')
            shown = matrix_metrics[matrix_metrics.competition == league].drop(columns=['competition'])
            st.dataframe(display_table(shown), hide_index=True, use_container_width=True)
        st.markdown('**W-H-W evidence · underlying Hybrid backtests**')
        whw_analysis.show_whw_history(metrics, embedded=True)

# Operational controls stay separate from the model explanations.
with st.expander('Refresh predictions · display or full cloud refresh'):
    st.caption('Refreshing the display only reloads existing published data; it does not train the models.')
    if st.button('Refresh displayed predictions', help='Reload the latest published snapshot; does not retrain models'):
        st.cache_data.clear()
        st.rerun()
    # Older cloud sessions may still hold the original no-argument refresh UI.
    # Never reload cloud_refresh_ui here: its in-memory login rate limit must
    # survive ordinary Streamlit reruns.
    if 'embedded' in inspect.signature(show_cloud_refresh).parameters:
        show_cloud_refresh(embedded=True)

# A legacy cached refresh helper owns its own expander. Render it outside this
# expander rather than nesting expanders or causing an unexpected-keyword crash.
if 'embedded' not in inspect.signature(show_cloud_refresh).parameters:
    show_cloud_refresh()


st.caption('Probabilities are estimates, not guarantees. Forecasts and historical player form can become stale; lineups and player availability are not confirmed.')
st.caption('League and team marks identify the competitions covered. All trademarks belong to their owners; no affiliation or endorsement is implied.')
